"""
/api/v1/recommendations — Core recommendation endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
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
    
    Flow:
    1. Load mood session from Firestore
    2. Load user's watch history (for CF scoring)
    3. Run the hybrid recommendation pipeline
    4. Persist result to Firestore for analytics
    5. Return recommendations to client
    """
    db = get_db()
    uid = user["uid"]

    # ── 1. Load mood session ───────────────────────────────────────────────────
    session_doc = db.collection("mood_sessions").document(payload.mood_session_id).get()
    if not session_doc.exists:
        raise HTTPException(status_code=404, detail="Mood session not found.")

    session_data = session_doc.to_dict()

    # Ensure session belongs to requesting user
    if session_data.get("uid") != uid:
        raise HTTPException(status_code=403, detail="Not authorized.")

    # ── 2. Load watch history ──────────────────────────────────────────────────
    history_docs = (
        db.collection("watch_history")
        .where("uid", "==", uid)
        .limit(500)  # Cap to last 500 entries for performance
        .stream()
    )
    watch_history = [d.to_dict() for d in history_docs]

    # Build set of already-watched title IDs to optionally exclude
    exclude_ids: set[str] = set()
    if payload.exclude_watched:
        exclude_ids = {e.get("title_id", "") for e in watch_history if e.get("title_id")}

    # ── 3. Generate recommendations ────────────────────────────────────────────
    recs, serendipity = await generate_recommendations(
        user_watch_history=watch_history,
        mood_session=session_data,
        limit=payload.limit,
        exclude_ids=exclude_ids,
    )

    # ── 4. Persist recommendation event for future analytics ──────────────────
    db.collection("recommendation_events").add({
        "uid": uid,
        "session_id": payload.mood_session_id,
        "moods": session_data.get("moods", []),
        "result_count": len(recs),
        "title_ids": [r.id for r in recs],
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
    """
    Store user feedback (thumbs up/down + optional rating).
    Used for future model improvement and A/B analytics.
    """
    db = get_db()
    db.collection("feedback").add({
        "uid": user["uid"],
        "title_id": payload.title_id,
        "session_id": payload.session_id,
        "relevant": payload.relevant,
        "mood_matched": payload.mood_matched,
        "rating": payload.rating,
    })
    return {"status": "ok"}
