"""
/api/v1/admin — Admin-only endpoints for model management.

These endpoints are protected by a simple admin token check.
Set ADMIN_SECRET in your .env to secure them.

Endpoints:
  POST /train    — trigger LightFM model training
  GET  /status   — check model status + data stats
  POST /save     — save trained model to disk
  POST /load     — load model from disk
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Header
from app.services.firebase import get_db
from app.services import lightfm_service
import logging

router  = APIRouter()
logger  = logging.getLogger(__name__)

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "changeme")


def verify_admin(x_admin_secret: str = Header(...)) -> None:
    """Simple header-based admin auth. Not for public APIs — internal use only."""
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret.")


@router.get("/status", summary="Model + data status")
async def model_status(_: None = Depends(verify_admin)):
    """
    Returns:
    - Whether LightFM model is trained and ready
    - Count of feedback records, unique users, unique titles
    - Count of onboarding vectors
    """
    db = get_db()

    feedback_docs = list(db.collection("feedback").stream())
    unique_users  = {d.to_dict().get("uid") for d in feedback_docs}
    unique_titles = {d.to_dict().get("title_id") for d in feedback_docs}

    onboarding_count = len(list(db.collection("onboarding_vectors").stream()))

    return {
        "lightfm_trained":       lightfm_service.is_trained(),
        "lightfm_available":     lightfm_service.LIGHTFM_AVAILABLE,
        "feedback_total":        len(feedback_docs),
        "unique_users":          len(unique_users),
        "unique_titles":         len(unique_titles),
        "onboarding_vectors":    onboarding_count,
        "ready_to_train":        len(unique_users) >= 50 and len(feedback_docs) >= 200,
        "min_users_needed":      max(0, 50 - len(unique_users)),
        "min_feedback_needed":   max(0, 200 - len(feedback_docs)),
    }


@router.post("/train", summary="Trigger LightFM model training")
async def train_model(_: None = Depends(verify_admin)):
    """
    Loads all feedback + onboarding vectors from Firestore and trains LightFM.

    This is a synchronous blocking call — training takes 30-120 seconds
    depending on data size. Call from a cron job or GitHub Action, not from
    user-facing flows.

    Returns training result + stats.
    """
    if not lightfm_service.LIGHTFM_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="LightFM not installed. Add 'lightfm scipy numpy' to requirements.txt"
        )

    db = get_db()

    # ── Load feedback records ──────────────────────────────────────────────────
    logger.info("Loading feedback records for LightFM training...")
    feedback_docs = list(db.collection("feedback").stream())
    feedback_records = [d.to_dict() for d in feedback_docs]

    if len(feedback_records) < 200:
        return {
            "success": False,
            "reason":  f"Not enough feedback ({len(feedback_records)} < 200 required)",
            "tip":     "Keep collecting thumbs up/down from users and try again later.",
        }

    # ── Load onboarding vectors (user features) ────────────────────────────────
    logger.info("Loading onboarding vectors...")
    ov_docs = list(db.collection("onboarding_vectors").stream())
    user_vectors = {
        d.id: d.to_dict().get("genre_vector", {})
        for d in ov_docs
    }

    # ── Train ──────────────────────────────────────────────────────────────────
    logger.info("Starting LightFM training with %d records, %d user vectors...",
                len(feedback_records), len(user_vectors))

    success = lightfm_service.train_model(feedback_records, user_vectors)

    if success:
        lightfm_service.save_model()
        return {
            "success":          True,
            "feedback_used":    len(feedback_records),
            "user_vectors":     len(user_vectors),
            "model_trained":    True,
        }
    else:
        return {
            "success": False,
            "reason":  "Training failed — check server logs for details.",
        }


@router.post("/save", summary="Save trained model to disk")
async def save_model(_: None = Depends(verify_admin)):
    """Serialize the current in-memory model to /tmp/lightfm_model.pkl"""
    ok = lightfm_service.save_model()
    return {"saved": ok}


@router.post("/load", summary="Load model from disk")
async def load_model(_: None = Depends(verify_admin)):
    """Load a previously saved model from /tmp/lightfm_model.pkl"""
    ok = lightfm_service.load_model()
    return {"loaded": ok, "model_ready": lightfm_service.is_trained()}
