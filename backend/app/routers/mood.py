"""
/api/v1/mood — Mood session endpoints.

A mood session is a lightweight Firestore doc keyed by a UUID.
It stores the selected moods + derived genre weights used by the
recommendation engine. Sessions expire after 24 h (handled by
a Firestore TTL policy in production).
"""

import uuid
from fastapi import APIRouter, Depends
from app.models.schemas import MoodSubmit, MoodResponse, MoodTag
from app.services.firebase import get_db
from app.dependencies import get_current_user

router = APIRouter()

# ── Mood → TMDB genre weight mapping ─────────────────────────────────────────
# Keys are TMDB genre names; values are weights applied during reranking.
# Weights are additive — a title can accumulate from multiple matching moods.

MOOD_GENRE_WEIGHTS: dict[MoodTag, dict[str, float]] = {
    MoodTag.UPLIFTING:    {"Comedy": 1.0, "Family": 0.8, "Animation": 0.7, "Music": 0.5},
    MoodTag.RELAXING:     {"Documentary": 0.9, "Animation": 0.7, "Romance": 0.6, "Drama": 0.5},
    MoodTag.THRILLING:    {"Action": 1.0, "Thriller": 1.0, "Crime": 0.7, "Mystery": 0.6},
    MoodTag.NOSTALGIC:    {"Family": 0.9, "Animation": 0.8, "Drama": 0.6, "History": 0.5},
    MoodTag.DARK:         {"Horror": 1.0, "Thriller": 0.9, "Crime": 0.8, "Mystery": 0.7},
    MoodTag.ROMANTIC:     {"Romance": 1.0, "Drama": 0.7, "Comedy": 0.4},
    MoodTag.ADVENTUROUS:  {"Adventure": 1.0, "Action": 0.8, "Fantasy": 0.7, "Science Fiction": 0.6},
    MoodTag.FUNNY:        {"Comedy": 1.0, "Animation": 0.6, "Family": 0.5},
    MoodTag.EMOTIONAL:    {"Drama": 1.0, "Romance": 0.7, "Animation": 0.5},
    MoodTag.MIND_BENDING: {"Science Fiction": 1.0, "Mystery": 0.9, "Thriller": 0.7, "Fantasy": 0.5},
}


def compute_genre_weights(moods: list[MoodTag]) -> dict[str, float]:
    """
    Aggregate genre weights from multiple moods.
    Weights are summed then normalized to [0, 1].
    """
    combined: dict[str, float] = {}
    for mood in moods:
        for genre, weight in MOOD_GENRE_WEIGHTS.get(mood, {}).items():
            combined[genre] = combined.get(genre, 0.0) + weight

    if not combined:
        return {}

    max_w = max(combined.values())
    return {g: round(w / max_w, 3) for g, w in combined.items()}


@router.post("/session", response_model=MoodResponse, summary="Create a mood session")
async def create_mood_session(
    payload: MoodSubmit,
    user: dict = Depends(get_current_user),
):
    """
    Accept user-selected moods, compute genre weights, persist a mood
    session document, and return the session ID for use in /recommendations.
    """
    session_id = str(uuid.uuid4())
    genre_weights = compute_genre_weights(payload.moods)

    db = get_db()
    db.collection("mood_sessions").document(session_id).set({
        "uid": user["uid"],
        "moods": [m.value for m in payload.moods],
        "intensity": payload.intensity,
        "genre_weights": genre_weights,
    })

    return MoodResponse(
        session_id=session_id,
        moods=payload.moods,
        genre_weights=genre_weights,
    )


@router.get("/history", summary="Get user's recent mood sessions")
async def get_mood_history(user: dict = Depends(get_current_user)):
    """Return the last 10 mood sessions for the authenticated user."""
    db = get_db()
    docs = (
        db.collection("mood_sessions")
        .where("uid", "==", user["uid"])
        .order_by("__name__", direction="DESCENDING")
        .limit(10)
        .stream()
    )
    return [{"session_id": d.id, **d.to_dict()} for d in docs]
