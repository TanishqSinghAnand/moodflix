"""
/api/v1/recommendations — Core recommendation endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import RecommendationRequest, RecommendationResponse, FeedbackPayload
from app.services.firebase import get_db
from app.services.recommender import generate_recommendations
from app.dependencies import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=RecommendationResponse, summary="Get mood-based recommendations")
async def get_recommendations(
    payload: RecommendationRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate personalized recommendations for the given mood session.

    V3 additions:
    - Loads onboarding_vector for cold-start users (no watch history yet)
    - Passes uid to recommender for LightFM scoring when model is trained
    """
    db  = get_db()
    uid = user["uid"]

    # ── Load mood session ──────────────────────────────────────────────────────
    session_doc = db.collection("mood_sessions").document(payload.mood_session_id).get()
    if not session_doc.exists:
        raise HTTPException(status_code=404, detail="Mood session not found.")

    session_data = session_doc.to_dict()
    if session_data.get("uid") != uid:
        raise HTTPException(status_code=403, detail="Not authorized.")

    # ── Load watch history ─────────────────────────────────────────────────────
    history_docs = (
        db.collection("watch_history")
        .where("uid", "==", uid)
        .limit(500)
        .stream()
    )
    watch_history = [d.to_dict() for d in history_docs]

    exclude_ids: set[str] = set()
    if payload.exclude_watched:
        exclude_ids = {e.get("title_id", "") for e in watch_history if e.get("title_id")}

    # ── Load onboarding vector (cold-start fallback) ───────────────────────────
    onboarding_vector: dict[str, float] | None = None
    if not watch_history:
        ov_doc = db.collection("onboarding_vectors").document(uid).get()
        if ov_doc.exists:
            onboarding_vector = ov_doc.to_dict().get("genre_vector")
            logger.info("Using onboarding vector for cold-start user %s", uid)

    # ── Generate recommendations ───────────────────────────────────────────────
    recs, serendipity = await generate_recommendations(
        user_watch_history=watch_history,
        mood_session=session_data,
        limit=payload.limit,
        exclude_ids=exclude_ids,
        uid=uid,
        onboarding_vector=onboarding_vector,
    )

    # ── Log recommendation event ───────────────────────────────────────────────
    db.collection("recommendation_events").add({
        "uid":        uid,
        "session_id": payload.mood_session_id,
        "moods":      session_data.get("moods", []),
        "result_count": len(recs),
        "title_ids":  [r.id for r in recs],
        "cold_start": onboarding_vector is not None and not watch_history,
    })

    return RecommendationResponse(
        session_id=payload.mood_session_id,
        moods=session_data.get("moods", []),
        results=recs,
        serendipity_pick=serendipity,
    )


@router.post("/feedback", summary="Submit feedback on a recommendation")
async def submit_feedback(
    payload: FeedbackPayload,
    user: dict = Depends(get_current_user),
):
    """Store user feedback. Used for LightFM model training."""
    db = get_db()
    db.collection("feedback").add({
        "uid":         user["uid"],
        "title_id":    payload.title_id,
        "session_id":  payload.session_id,
        "relevant":    payload.relevant,
        "mood_matched": payload.mood_matched,
        "rating":      payload.rating,
    })
    return {"status": "ok"}
