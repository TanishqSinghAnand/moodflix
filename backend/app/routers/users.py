"""Users router — profile management."""
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.services.firebase import get_db
from app.models.schemas import UserProfile

router = APIRouter()

@router.get("/profile", response_model=UserProfile, summary="Get user profile")
async def get_profile(user: dict = Depends(get_current_user)):
    db = get_db()
    doc = db.collection("users").document(user["uid"]).get()
    if not doc.exists:
        # Auto-create profile on first access
        profile = {"uid": user["uid"], "display_name": user.get("name"), "watch_count": 0, "onboarding_complete": False, "favorite_genres": [], "avatar_url": user.get("picture")}
        db.collection("users").document(user["uid"]).set(profile)
        return UserProfile(**profile)
    return UserProfile(**doc.to_dict())

@router.patch("/profile", summary="Update user profile")
async def update_profile(updates: dict, user: dict = Depends(get_current_user)):
    # Only allow safe fields to be updated
    allowed = {"display_name", "favorite_genres", "onboarding_complete", "avatar_url"}
    safe = {k: v for k, v in updates.items() if k in allowed}
    db = get_db()
    db.collection("users").document(user["uid"]).update(safe)
    return {"status": "updated"}
