"""
/api/v1/onboarding — Cold-start onboarding quiz endpoint.

Problem: New users with no watch history get purely mood-based recommendations
because their CF score is 0 for everything.

Solution: A short quiz where users pick genres they love + optionally name
some favourite titles. We build a SYNTHETIC watch history vector from their
answers and store it in Firestore under "onboarding_vector".

The recommender checks for this vector when watch_history is empty, giving
personalised recs even before any CSV is uploaded.

LightFM integration note:
  Once enough users have completed onboarding + given feedback, we can train
  a LightFM model using:
    - onboarding_vector as user features
    - feedback (thumbs up/down) as implicit interactions
    - genre tags as item features
  The trained model replaces the cosine CF step in recommender.py.
"""

import math
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import OnboardingSubmit, OnboardingResponse
from app.services.firebase import get_db
from app.dependencies import get_current_user

router = APIRouter()

# ── Genre → synthetic watch count mapping ─────────────────────────────────────
# Maps quiz genre choices to how many "virtual watches" to inject per strength level.
# strength 1 = casual interest, 2 = like it, 3 = love it
STRENGTH_TO_WATCHES = {1: 5, 2: 15, 3: 30}

# Media preference → genre boost
# If someone says they love anime, we boost Animation + a few anime-adjacent genres
MEDIA_PREFERENCE_BOOSTS: dict[str, dict[str, int]] = {
    "movies":  {"Drama": 5, "Action": 5, "Comedy": 5},
    "series":  {"Drama": 8, "Crime": 5, "Mystery": 5},
    "anime":   {"Animation": 20, "Fantasy": 8, "Adventure": 8, "Science Fiction": 5},
    "both":    {},
}

# All valid TMDB genre names (for validation)
VALID_GENRES = {
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
    "Romance", "Science Fiction", "Thriller", "War", "Western",
}


def _build_synthetic_vector(submit: OnboardingSubmit) -> dict[str, float]:
    """
    Convert quiz answers into a normalized genre preference vector.

    Logic:
    1. For each selected genre, add (strength × watch_count) virtual watches
    2. Apply media preference boost on top
    3. L1-normalize to [0, 1]

    This vector is stored in Firestore and used exactly like a real watch
    history vector in the recommender — it just comes from quiz answers
    instead of imported CSV files.
    """
    raw_counts: dict[str, float] = {}

    # Step 1: Genre choices with strength weighting
    for choice in submit.genres:
        genre = choice.genre.strip().title()
        if genre not in VALID_GENRES:
            continue
        virtual_watches = STRENGTH_TO_WATCHES.get(choice.strength, 10)
        raw_counts[genre] = raw_counts.get(genre, 0.0) + virtual_watches

    # Step 2: Media preference boost
    boosts = MEDIA_PREFERENCE_BOOSTS.get(submit.media_preference, {})
    for genre, extra in boosts.items():
        raw_counts[genre] = raw_counts.get(genre, 0.0) + extra

    # Step 3: Normalize
    total = sum(raw_counts.values()) or 1.0
    return {g: round(c / total, 4) for g, c in raw_counts.items()}


@router.post("/complete", response_model=OnboardingResponse, summary="Submit onboarding quiz")
async def complete_onboarding(
    payload: OnboardingSubmit,
    user: dict = Depends(get_current_user),
):
    """
    Process onboarding quiz answers and build a synthetic preference vector.

    Stores:
    - onboarding_vector: normalized genre weights (used as cold-start CF input)
    - favorite_titles: stored for future TMDB matching
    - media_preference: used to bias movie/series/anime ratio in diversity filter
    - onboarding_complete: True (gates the onboarding UI from showing again)
    """
    if not payload.genres:
        raise HTTPException(400, "Please select at least 3 genres.")

    genre_vector = _build_synthetic_vector(payload)

    db  = get_db()
    uid = user["uid"]

    # Update user profile
    db.collection("users").document(uid).set({
        "uid":                 uid,
        "onboarding_complete": True,
        "favorite_genres":     [c.genre for c in payload.genres],
        "media_preference":    payload.media_preference,
    }, merge=True)

    # Store synthetic vector separately (used by recommender)
    db.collection("onboarding_vectors").document(uid).set({
        "uid":             uid,
        "genre_vector":    genre_vector,
        "favorite_titles": payload.favorite_titles,
        "media_preference": payload.media_preference,
    })

    return OnboardingResponse(
        success=True,
        message="Onboarding complete! Your first recommendations are ready.",
        genre_vector=genre_vector,
    )


@router.get("/status", summary="Check if user has completed onboarding")
async def onboarding_status(user: dict = Depends(get_current_user)):
    """Returns whether the user has completed onboarding and their preferences."""
    db  = get_db()
    doc = db.collection("users").document(user["uid"]).get()
    if not doc.exists:
        return {"onboarding_complete": False}
    data = doc.to_dict()
    return {
        "onboarding_complete": data.get("onboarding_complete", False),
        "media_preference":    data.get("media_preference", "both"),
        "favorite_genres":     data.get("favorite_genres", []),
    }
