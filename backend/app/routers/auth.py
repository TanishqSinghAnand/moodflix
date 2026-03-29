"""Auth router — minimal, since Firebase handles identity."""
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.services.firebase import get_db

router = APIRouter()

@router.get("/me", summary="Verify token and return uid")
async def me(user: dict = Depends(get_current_user)):
    """Lightweight endpoint for client-side token validation."""
    return {"uid": user["uid"], "email": user.get("email")}
