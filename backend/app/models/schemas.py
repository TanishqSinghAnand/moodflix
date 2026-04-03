"""
Pydantic v2 models used for request validation and response serialization.
Shared between web and future React Native clients via the same API contract.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


# ── Mood ──────────────────────────────────────────────────────────────────────

class MoodTag(str, Enum):
    UPLIFTING    = "uplifting"
    RELAXING     = "relaxing"
    THRILLING    = "thrilling"
    NOSTALGIC    = "nostalgic"
    DARK         = "dark"
    ROMANTIC     = "romantic"
    ADVENTUROUS  = "adventurous"
    FUNNY        = "funny"
    EMOTIONAL    = "emotional"
    MIND_BENDING = "mind_bending"


class MoodIntensity(BaseModel):
    """
    Per-mood intensity value (1-10).
    Allows each selected mood to carry a different weight.
    e.g. Funny at 8 + Relaxing at 3 → recommendations lean more funny.
    """
    mood:      MoodTag
    intensity: int = Field(5, ge=1, le=10)


class MoodSubmit(BaseModel):
    """Payload sent by the client when user selects their current mood."""
    moods: list[MoodIntensity] = Field(
        ..., min_length=1, max_length=3,
        description="1-3 mood+intensity pairs selected by user"
    )


class MoodResponse(BaseModel):
    session_id:    str
    moods:         list[MoodTag]
    intensities:   dict[str, int]
    genre_weights: dict[str, float]


# ── Media / Titles ─────────────────────────────────────────────────────────────

class Platform(str, Enum):
    NETFLIX  = "netflix"
    PRIME    = "prime"
    HOTSTAR  = "hotstar"
    MAL      = "myanimelist"
    UNKNOWN  = "unknown"


class MediaType(str, Enum):
    MOVIE  = "movie"
    SERIES = "series"
    ANIME  = "anime"


class Title(BaseModel):
    id:           str
    title:        str
    media_type:   MediaType
    platform:     Optional[Platform] = None
    genres:       list[str] = []
    mood_tags:    list[MoodTag] = []
    poster_url:   Optional[str] = None
    backdrop_url: Optional[str] = None
    overview:     Optional[str] = None
    release_year: Optional[int] = None
    rating:       Optional[float] = None
    mal_score:    Optional[float] = None


class WatchEvent(BaseModel):
    title:      str
    platform:   Platform
    watched_at: Optional[str] = None
    episode:    Optional[str] = None


# ── Recommendations ────────────────────────────────────────────────────────────

class RecommendationRequest(BaseModel):
    mood_session_id: str
    limit:           int  = Field(12, ge=1, le=50)
    exclude_watched: bool = True


class RecommendedTitle(Title):
    mood_score:  float = Field(..., description="0-1 alignment with requested mood")
    cf_score:    float = Field(..., description="0-1 collaborative filtering score")
    final_score: float
    reason:      str   = Field(..., description="Human-readable reason string shown in UI")


class RecommendationResponse(BaseModel):
    session_id:       str
    moods:            list[MoodTag]
    results:          list[RecommendedTitle]
    serendipity_pick: Optional[RecommendedTitle] = None


# ── Import ─────────────────────────────────────────────────────────────────────

class ImportResult(BaseModel):
    platform:     Platform
    parsed_count: int
    new_titles:   int
    skipped:      int
    errors:       list[str] = []


# ── Onboarding ─────────────────────────────────────────────────────────────────

class OnboardingGenreChoice(BaseModel):
    """
    A genre the user selected during onboarding quiz.
    strength: 1=mild interest, 2=like it, 3=love it
    """
    genre:    str
    strength: int = Field(2, ge=1, le=3)


class OnboardingSubmit(BaseModel):
    """
    Payload sent after the onboarding quiz is completed.
    Builds a synthetic watch vector so cold-start users get personalized recs.
    """
    genres:           list[OnboardingGenreChoice] = Field(..., min_length=3, max_length=15)
    favorite_titles:  list[str]                   = Field(default=[], max_length=10)
    media_preference: Literal["movies", "series", "both", "anime"] = "both"


class OnboardingResponse(BaseModel):
    success:      bool
    message:      str
    genre_vector: dict[str, float]


# ── User ──────────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    uid:                 str
    display_name:        Optional[str] = None
    avatar_url:          Optional[str] = None
    favorite_genres:     list[str] = []
    watch_count:         int = 0
    onboarding_complete: bool = False
    media_preference:    str = "both"


class FeedbackPayload(BaseModel):
    title_id:     str
    session_id:   str
    relevant:     bool
    mood_matched: Optional[bool] = None
    rating:       Optional[int]  = Field(None, ge=1, le=5)
