"""
Recommendation Engine — hybrid CF + mood reranking.

V2 Improvements over V1:
  1. Popularity boost   — well-rated popular titles score higher
  2. Recency weighting  — recently watched genres carry more weight
  3. Genre diversity    — final results capped per genre (max 3 per genre)
                          + ensures mix of movies/series/anime

Pipeline:
  1. Load user's watch history → build RECENCY-WEIGHTED genre preference vector
  2. Fetch candidate titles from TMDB (genre-filtered)
  3. Score each candidate:
       cf_score         = cosine similarity(user vector, title genre vector)
       mood_score       = cosine similarity(title genres, mood genre weights)
       popularity_score = log-normalized TMDB vote count + rating
       final_score      = 0.4*cf + 0.4*mood + 0.2*popularity
  4. Apply genre diversity cap to final results
  5. Inject serendipity pick (high mood, low CF)
  6. Return top-N diverse results
"""

from __future__ import annotations
import math
import random
import httpx
import logging
from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import RecommendedTitle, MediaType, MoodTag
from app.services import lightfm_service

logger = logging.getLogger(__name__)

# ── Genre universe (TMDB genre IDs) ───────────────────────────────────────────
TMDB_GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}

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

# ── Diversity config ───────────────────────────────────────────────────────────
MAX_PER_GENRE  = 2   # max titles sharing the same primary genre (was 3)
MAX_PER_TYPE   = 6   # max movies OR series out of 12 total (was 8)
MAX_ANIMATION  = 3   # hard cap on Animation-primary titles
MIN_MOVIES     = 3   # guaranteed minimum movies in every result set
MIN_SERIES     = 3   # guaranteed minimum series in every result set


# ── Helpers ────────────────────────────────────────────────────────────────────

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
    dot   = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Improvement 2: Recency-weighted user vector ────────────────────────────────

def _recency_weight(watched_at_str: str | None) -> float:
    """
    Returns a weight between 0.1 and 1.0 based on how recently something was watched.
    - Watched today       → 1.0
    - Watched 30 days ago → ~0.6
    - Watched 1 year ago  → ~0.2
    - No date             → 0.3 (moderate default)
    Formula: 1 / (1 + log(days_ago + 1))
    """
    if not watched_at_str:
        return 0.3
    try:
        date_part    = watched_at_str[:10]
        watched_date = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_ago     = max((datetime.now(timezone.utc) - watched_date).days, 0)
        return round(1.0 / (1.0 + math.log(days_ago + 1)), 4)
    except Exception:
        return 0.3


def _build_user_vector(watch_history: list[dict]) -> dict[str, float]:
    """
    Build a recency-weighted genre preference vector from watch history.
    Recent watches carry more weight than old ones.
    Result is L1-normalized to [0, 1].
    """
    weighted_counts: dict[str, float] = {}
    for entry in watch_history:
        weight = _recency_weight(entry.get("watched_at"))
        for genre in entry.get("genres", []):
            weighted_counts[genre] = weighted_counts.get(genre, 0.0) + weight
    total = sum(weighted_counts.values()) or 1.0
    return {g: round(c / total, 4) for g, c in weighted_counts.items()}


# ── Improvement 1: Popularity score ───────────────────────────────────────────

_MAX_LOG_VOTES = math.log(35_000 + 1)
_MAX_RATING    = 10.0


def _popularity_score(raw: dict) -> float:
    """
    Compute a 0-1 popularity score combining vote count (log-scaled) and rating.
    Formula: 0.6 * log_normalized_votes + 0.4 * normalized_rating
    Log scaling prevents mega-blockbusters from dominating everything.
    """
    vote_count  = raw.get("vote_count", 0) or 0
    vote_avg    = raw.get("vote_average", 0.0) or 0.0
    log_votes   = math.log(vote_count + 1) / _MAX_LOG_VOTES
    norm_rating = vote_avg / _MAX_RATING
    return round(min(0.6 * log_votes + 0.4 * norm_rating, 1.0), 4)


# ── TMDB fetching ──────────────────────────────────────────────────────────────

async def _fetch_tmdb_candidates(genre_weights: dict[str, float], limit: int = 50) -> list[dict]:
    """
    Fetch movies + TV shows from TMDB filtered by top mood genres.
    Fetches 2 pages per type for a richer, more diverse candidate pool.
    Filters out titles with fewer than 50 votes (avoids obscure low-quality results).
    """
    if not settings.TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not set — returning empty candidates.")
        return []

    top_genres   = sorted(genre_weights.items(), key=lambda x: x[1], reverse=True)[:3]
    genre_id_map = {v: k for k, v in TMDB_GENRE_MAP.items()}
    genre_ids    = [str(genre_id_map[g]) for g, _ in top_genres if g in genre_id_map]

    base_params = {
        "api_key":        settings.TMDB_API_KEY,
        "with_genres":    ",".join(genre_ids),
        "sort_by":        "popularity.desc",
        "vote_count.gte": 50,  # filter out very obscure titles
    }

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=10) as client:
        for endpoint in ["discover/movie", "discover/tv"]:
            for page in [1, 2]:
                try:
                    r = await client.get(
                        f"{settings.TMDB_BASE_URL}/{endpoint}",
                        params={**base_params, "page": page},
                    )
                    r.raise_for_status()
                    results.extend(r.json().get("results", []))
                except Exception as exc:
                    logger.error("TMDB fetch error for %s page %s: %s", endpoint, page, exc)

    # Deduplicate by TMDB id
    seen: set[int] = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)

    return unique


# ── Scoring ────────────────────────────────────────────────────────────────────

def _score_candidate(
    candidate: dict,
    user_vector: dict[str, float],
    genre_weights: dict[str, float],
    moods: list[MoodTag],
) -> tuple[float, float, float, float]:
    """
    Score a single candidate. Returns (cf, mood, popularity, final).
    Weights: 40% CF + 40% Mood + 20% Popularity
    """
    genres       = _genres_from_ids(candidate.get("genre_ids", []))
    title_vector = {g: 1.0 for g in genres}

    cf_score   = _cosine(user_vector, title_vector)
    mood_score = _cosine(title_vector, genre_weights)
    pop_score  = _popularity_score(candidate)
    final      = 0.4 * cf_score + 0.4 * mood_score + 0.2 * pop_score

    return round(cf_score, 4), round(mood_score, 4), round(pop_score, 4), round(final, 4)


# ── Improvement 3: Genre diversity ────────────────────────────────────────────

def _apply_diversity(
    scored: list[tuple[float, float, float, float, dict]],
    limit: int,
    serendipity_id: str | None,
) -> list[tuple[float, float, float, float, dict]]:
    """
    Select top-N results with strict mix enforcement.

    Rules (for a limit of 12):
    - Max 2 titles per primary genre (was 3) — prevents genre monotony
    - Max 3 Animation-primary titles — stops all-anime results
    - Max 6 movies OR 6 series — guarantees both types appear
    - GUARANTEED minimums: at least 3 movies + 3 series always included
      even if their scores are lower (two-pass selection)

    Two-pass approach:
      Pass 1: score-ordered selection respecting all caps
      Pass 2: if minimums not met, backfill from remaining candidates
    """
    genre_counts:  dict[str, int] = {}
    type_counts:   dict[str, int] = {"movie": 0, "series": 0}
    anim_count:    int = 0
    selected = []
    remaining = []  # candidates not selected in pass 1 (for backfill)

    # ── Pass 1: score-ordered selection with caps ─────────────────────────────
    for item in scored:
        cf, mood, pop, final, raw = item

        if f"tmdb-{raw['id']}" == serendipity_id:
            continue

        genres     = _genres_from_ids(raw.get("genre_ids", []))
        primary    = genres[0] if genres else "Unknown"
        media_type = "movie" if "title" in raw else "series"
        is_anim    = primary == "Animation"

        # Apply caps
        if genre_counts.get(primary, 0) >= MAX_PER_GENRE:
            remaining.append(item)
            continue
        if type_counts[media_type] >= MAX_PER_TYPE:
            remaining.append(item)
            continue
        if is_anim and anim_count >= MAX_ANIMATION:
            remaining.append(item)
            continue

        genre_counts[primary]   = genre_counts.get(primary, 0) + 1
        type_counts[media_type] += 1
        if is_anim:
            anim_count += 1
        selected.append(item)

        if len(selected) >= limit:
            break

    # ── Pass 2: backfill to hit guaranteed minimums ───────────────────────────
    # If we don't have enough movies, pull best-scoring movies from remaining
    for media_type, minimum in [("movie", MIN_MOVIES), ("series", MIN_SERIES)]:
        if type_counts[media_type] >= minimum:
            continue  # already have enough

        needed = minimum - type_counts[media_type]
        backfill_pool = [
            item for item in remaining
            if ("title" in item[4]) == (media_type == "movie")
            and f"tmdb-{item[4]['id']}" not in {f"tmdb-{s[4]['id']}" for s in selected}
        ]

        for item in backfill_pool[:needed]:
            cf, mood, pop, final, raw = item
            media_type_item = "movie" if "title" in raw else "series"
            type_counts[media_type_item] += 1
            selected.append(item)

    # Re-sort selected by final score (backfilled items may have lower scores)
    selected.sort(key=lambda x: x[3], reverse=True)
    return selected[:limit]


# ── Title builder ──────────────────────────────────────────────────────────────

def _build_reason(moods: list[MoodTag], genres: list[str], is_serendipity: bool, pop_score: float) -> str:
    if is_serendipity:
        return "✨ Something new — step outside your comfort zone"
    mood_labels  = [m.value.replace("_", " ") for m in moods[:2]]
    genre_labels = genres[:2]
    parts        = []
    if mood_labels:
        parts.append(f"Matches your {' & '.join(mood_labels)} vibe")
    if genre_labels:
        parts.append(f"({', '.join(genre_labels)})")
    if pop_score > 0.7:
        parts.append("· Highly rated")
    return " ".join(parts) or "Picked for you"


def _tmdb_to_title(
    raw: dict,
    cf_score: float,
    mood_score: float,
    pop_score: float,
    final_score: float,
    moods: list[MoodTag],
    is_serendipity: bool = False,
) -> RecommendedTitle:
    genres    = _genres_from_ids(raw.get("genre_ids", []))
    mood_tags = _mood_tags_from_genres(genres)
    is_movie  = "title" in raw

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
            int(raw.get("release_date", "0000")[:4])
            if raw.get("release_date") else None
        ),
        rating=raw.get("vote_average"),
        cf_score=cf_score,
        mood_score=mood_score,
        final_score=final_score,
        reason=_build_reason(moods, genres, is_serendipity, pop_score),
    )


# ── Main entry point ───────────────────────────────────────────────────────────

async def generate_recommendations(
    user_watch_history: list[dict],
    mood_session: dict,
    limit: int = 12,
    exclude_ids: set[str] | None = None,
    uid: str | None = None,
    onboarding_vector: dict[str, float] | None = None,
) -> tuple[list[RecommendedTitle], RecommendedTitle | None]:
    """
    Full V3 recommendation pipeline.

    New in V3:
    - uid + onboarding_vector: used for cold-start personalisation
    - LightFM scores: blended in when model is trained and user is known
    - Onboarding vector used as fallback when watch_history is empty

    Score composition:
      If LightFM trained + user known:
        final = 0.35*lightfm + 0.3*mood + 0.2*cf_cosine + 0.15*popularity
      Else (cosine fallback):
        final = 0.4*cf_cosine + 0.4*mood + 0.2*popularity

    Returns: (recommendations, serendipity_pick)
    """
    moods         = [MoodTag(m) for m in mood_session.get("moods", [])]
    genre_weights = mood_session.get("genre_weights", {})
    exclude_ids   = exclude_ids or set()

    # ── Step 1: Build user preference vector ──────────────────────────────────
    # Priority: real watch history > onboarding vector > empty (cold start)
    user_vector = _build_user_vector(user_watch_history)

    if not user_vector and onboarding_vector:
        # Cold-start: use synthetic vector from onboarding quiz
        user_vector = onboarding_vector
        logger.info("Cold start — using onboarding vector for uid=%s", uid)
    elif not user_vector:
        logger.info("Cold start — no history or onboarding vector, mood-only scoring")

    # ── Step 2: Fetch candidates from TMDB ────────────────────────────────────
    candidates = await _fetch_tmdb_candidates(genre_weights, limit=settings.CF_CANDIDATE_POOL_SIZE)

    # ── Step 3: Get LightFM scores if model available ─────────────────────────
    use_lightfm = lightfm_service.is_trained() and uid is not None
    lightfm_scores: dict[str, float] = {}

    if use_lightfm:
        candidate_ids  = [f"tmdb-{c['id']}" for c in candidates]
        raw_lfm_scores = lightfm_service.score_candidates(uid, candidate_ids, user_vector)

        if raw_lfm_scores:
            # Normalize LightFM scores to [0, 1] using min-max scaling
            vals = list(raw_lfm_scores.values())
            min_v, max_v = min(vals), max(vals)
            rng = max_v - min_v or 1.0
            lightfm_scores = {k: round((v - min_v) / rng, 4) for k, v in raw_lfm_scores.items()}
            logger.info("LightFM scores available for %d candidates", len(lightfm_scores))
        else:
            use_lightfm = False  # user not in training set, fall back to cosine
            logger.debug("LightFM returned no scores — cosine fallback")

    # ── Step 4: Score all candidates ──────────────────────────────────────────
    scored: list[tuple[float, float, float, float, dict]] = []

    for c in candidates:
        title_id = f"tmdb-{c['id']}"
        if title_id in exclude_ids:
            continue

        cf, mood, pop, _ = _score_candidate(c, user_vector, genre_weights, moods)

        if use_lightfm and title_id in lightfm_scores:
            # Blend: LightFM captures deep collaborative patterns, cosine fills gaps
            lfm   = lightfm_scores[title_id]
            final = 0.35 * lfm + 0.30 * mood + 0.20 * cf + 0.15 * pop
        else:
            # Pure cosine fallback
            final = 0.40 * cf + 0.40 * mood + 0.20 * pop

        scored.append((cf, mood, pop, round(final, 4), c))

    scored.sort(key=lambda x: x[3], reverse=True)

    # ── Step 5: Serendipity pick ───────────────────────────────────────────────
    serendipity_pick: RecommendedTitle | None = None
    discovery_pool = [s for s in scored if s[0] < 0.2 and s[1] > 0.4 and s[2] > 0.3]
    if discovery_pool:
        pick = random.choice(discovery_pool[:5])
        cf, mood, pop, final, raw = pick
        serendipity_pick = _tmdb_to_title(raw, cf, mood, pop, final, moods, is_serendipity=True)

    serendipity_id = serendipity_pick.id if serendipity_pick else None

    # ── Step 6: Genre-diverse top-N selection ─────────────────────────────────
    diverse = _apply_diversity(scored, limit, serendipity_id)

    # ── Step 7: Build response objects ────────────────────────────────────────
    recs = [_tmdb_to_title(raw, cf, mood, pop, final, moods) for cf, mood, pop, final, raw in diverse]

    logger.info(
        "Recs: %d returned | candidates=%d | lightfm=%s | uid=%s",
        len(recs), len(candidates), use_lightfm, uid
    )
    return recs, serendipity_pick
