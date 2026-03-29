"""
Recommendation Engine — hybrid CF + mood reranking.

Pipeline:
  1. Load user's watch history from Firestore → build genre preference vector
  2. Fetch candidate titles from TMDB (trending + genre-filtered)
  3. Score each candidate:
       cf_score    = cosine similarity of title genre vector vs user preference vector
       mood_score  = dot product of title genres vs session genre weights
       final_score = 0.5 * cf_score + 0.5 * mood_score  (tunable α)
  4. Inject one serendipity pick (high mood score, low cf_score = discovery)
  5. Return top-N results

This design is intentionally lightweight — no ML training infra needed for V1.
A future V2 can swap step 1–3 for a proper matrix factorization model trained
offline and served via a vector DB (e.g. Pinecone or Vertex AI Matching Engine).
"""

from __future__ import annotations
import asyncio
import math
import random
import httpx
import logging
from typing import Optional

from app.config import settings
from app.models.schemas import RecommendedTitle, MediaType, MoodTag, Platform

logger = logging.getLogger(__name__)

# ── Genre universe (TMDB genre IDs) ───────────────────────────────────────────
TMDB_GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}

# Mood tags inferred from genre combinations (simple heuristic for V1)
GENRE_TO_MOOD: dict[str, list[MoodTag]] = {
    "Action":           [MoodTag.THRILLING, MoodTag.ADVENTUROUS],
    "Adventure":        [MoodTag.ADVENTUROUS],
    "Animation":        [MoodTag.UPLIFTING, MoodTag.NOSTALGIC, MoodTag.FUNNY],
    "Comedy":           [MoodTag.FUNNY, MoodTag.UPLIFTING],
    "Crime":            [MoodTag.DARK, MoodTag.THRILLING],
    "Documentary":      [MoodTag.RELAXING],
    "Drama":            [MoodTag.EMOTIONAL, MoodTag.RELAXING],
    "Family":           [MoodTag.UPLIFTING, MoodTag.NOSTALGIC],
    "Fantasy":          [MoodTag.ADVENTUROUS, MoodTag.MIND_BENDING],
    "Horror":           [MoodTag.DARK, MoodTag.THRILLING],
    "Music":            [MoodTag.UPLIFTING, MoodTag.EMOTIONAL],
    "Mystery":          [MoodTag.MIND_BENDING, MoodTag.DARK],
    "Romance":          [MoodTag.ROMANTIC, MoodTag.EMOTIONAL],
    "Science Fiction":  [MoodTag.MIND_BENDING, MoodTag.ADVENTUROUS],
    "Thriller":         [MoodTag.THRILLING, MoodTag.DARK],
}


def _genres_from_ids(genre_ids: list[int]) -> list[str]:
    return [TMDB_GENRE_MAP[g] for g in genre_ids if g in TMDB_GENRE_MAP]


def _mood_tags_from_genres(genres: list[str]) -> list[MoodTag]:
    tags: set[MoodTag] = set()
    for g in genres:
        tags.update(GENRE_TO_MOOD.get(g, []))
    return list(tags)


def _cosine(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity between two sparse genre vectors."""
    keys = set(vec_a) & set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _build_user_vector(watch_history: list[dict]) -> dict[str, float]:
    """
    Build a genre preference vector from raw watch history.
    Each watched genre increments its count; result is L1-normalized.
    """
    counts: dict[str, float] = {}
    for entry in watch_history:
        for genre in entry.get("genres", []):
            counts[genre] = counts.get(genre, 0.0) + 1.0

    total = sum(counts.values()) or 1.0
    return {g: c / total for g, c in counts.items()}


async def _fetch_tmdb_candidates(genre_weights: dict[str, float], limit: int = 50) -> list[dict]:
    """
    Fetch trending movies + shows from TMDB.
    Uses genre_weights to bias the genre filter parameters.
    Returns raw TMDB result dicts.
    """
    if not settings.TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not set — returning empty candidates.")
        return []

    # Pick top 3 genres by weight to use as TMDB genre filter
    top_genres = sorted(genre_weights.items(), key=lambda x: x[1], reverse=True)[:3]
    genre_id_map = {v: k for k, v in TMDB_GENRE_MAP.items()}
    genre_ids = [str(genre_id_map[g]) for g, _ in top_genres if g in genre_id_map]

    params = {
        "api_key": settings.TMDB_API_KEY,
        "with_genres": ",".join(genre_ids),
        "sort_by": "popularity.desc",
        "page": 1,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        results = []
        for endpoint in ["discover/movie", "discover/tv"]:
            try:
                r = await client.get(f"{settings.TMDB_BASE_URL}/{endpoint}", params=params)
                r.raise_for_status()
                results.extend(r.json().get("results", [])[:limit // 2])
            except Exception as exc:
                logger.error("TMDB fetch error for %s: %s", endpoint, exc)

    return results


def _score_candidate(
    candidate: dict,
    user_vector: dict[str, float],
    genre_weights: dict[str, float],
    mood_tags: list[MoodTag],
    alpha: float = 0.5,
) -> tuple[float, float, float]:
    """
    Score a single candidate title.
    Returns (cf_score, mood_score, final_score).
    alpha controls the CF vs mood tradeoff (0=all mood, 1=all CF).
    """
    genres = _genres_from_ids(candidate.get("genre_ids", []))
    title_vector = {g: 1.0 for g in genres}

    cf_score    = _cosine(user_vector, title_vector)
    mood_score  = _cosine(title_vector, genre_weights)
    final_score = alpha * cf_score + (1 - alpha) * mood_score

    return round(cf_score, 4), round(mood_score, 4), round(final_score, 4)


def _build_reason(moods: list[MoodTag], genres: list[str], is_serendipity: bool) -> str:
    """Generate a short human-readable reason string for the UI."""
    if is_serendipity:
        return "✨ Something new — step outside your comfort zone"
    mood_labels = [m.value.replace("_", " ") for m in moods[:2]]
    genre_labels = genres[:2]
    parts = []
    if mood_labels:
        parts.append(f"Matches your {' & '.join(mood_labels)} vibe")
    if genre_labels:
        parts.append(f"({', '.join(genre_labels)})")
    return " ".join(parts) or "Picked for you"


def _tmdb_to_title(
    raw: dict,
    cf_score: float,
    mood_score: float,
    final_score: float,
    moods: list[MoodTag],
    is_serendipity: bool = False,
) -> RecommendedTitle:
    """Convert a raw TMDB result dict into a RecommendedTitle model."""
    genres   = _genres_from_ids(raw.get("genre_ids", []))
    mood_tags = _mood_tags_from_genres(genres)
    is_movie  = "title" in raw  # TMDB uses "title" for movies, "name" for TV

    return RecommendedTitle(
        id=f"tmdb-{raw['id']}",
        title=raw.get("title") or raw.get("name", "Unknown"),
        media_type=MediaType.MOVIE if is_movie else MediaType.SERIES,
        genres=genres,
        mood_tags=mood_tags,
        poster_url=(
            f"https://image.tmdb.org/t/p/w500{raw['poster_path']}"
            if raw.get("poster_path") else None
        ),
        backdrop_url=(
            f"https://image.tmdb.org/t/p/w1280{raw['backdrop_path']}"
            if raw.get("backdrop_path") else None
        ),
        overview=raw.get("overview"),
        release_year=(
            int(raw.get("release_date", "0")[:4]) if raw.get("release_date") else None
        ),
        rating=raw.get("vote_average"),
        cf_score=cf_score,
        mood_score=mood_score,
        final_score=final_score,
        reason=_build_reason(moods, genres, is_serendipity),
    )


async def generate_recommendations(
    user_watch_history: list[dict],
    mood_session: dict,
    limit: int = 12,
    exclude_ids: set[str] | None = None,
) -> tuple[list[RecommendedTitle], RecommendedTitle | None]:
    """
    Main entry point for the recommendation pipeline.

    Returns:
        (recommendations, serendipity_pick)
    """
    moods         = [MoodTag(m) for m in mood_session.get("moods", [])]
    genre_weights = mood_session.get("genre_weights", {})
    exclude_ids   = exclude_ids or set()

    # Step 1: Build user preference vector from watch history
    user_vector = _build_user_vector(user_watch_history)

    # Step 2: Fetch candidates from TMDB
    candidates = await _fetch_tmdb_candidates(genre_weights, limit=settings.CF_CANDIDATE_POOL_SIZE)

    # Step 3: Score & filter candidates
    scored: list[tuple[float, float, float, dict]] = []
    for c in candidates:
        if f"tmdb-{c['id']}" in exclude_ids:
            continue
        cf, mood, final = _score_candidate(c, user_vector, genre_weights, moods)
        scored.append((cf, mood, final, c))

    # Sort by final score descending
    scored.sort(key=lambda x: x[2], reverse=True)

    # Step 4: Pick serendipity item (high mood score, low CF — a discovery)
    serendipity_pick: RecommendedTitle | None = None
    discovery_candidates = [s for s in scored if s[0] < 0.2 and s[1] > 0.4]
    if discovery_candidates:
        pick = random.choice(discovery_candidates[:5])
        cf, mood, final, raw = pick
        serendipity_pick = _tmdb_to_title(raw, cf, mood, final, moods, is_serendipity=True)

    # Step 5: Top-N recommendations (exclude serendipity pick)
    serendipity_id = serendipity_pick.id if serendipity_pick else None
    recs = []
    for cf, mood, final, raw in scored:
        if len(recs) >= limit:
            break
        t = _tmdb_to_title(raw, cf, mood, final, moods)
        if t.id != serendipity_id:
            recs.append(t)

    return recs, serendipity_pick