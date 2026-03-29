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
    UPLIFTING   = "uplifting"
    RELAXING    = "relaxing"
    THRILLING   = "thrilling"
    NOSTALGIC   = "nostalgic"
    DARK        = "dark"
    ROMANTIC    = "romantic"
    ADVENTUROUS = "adventurous"
    FUNNY       = "funny"
    EMOTIONAL   = "emotional"
    MIND_BENDING = "mind_bending"


class MoodSubmit(BaseModel):
    """Payload sent by the client when user selects their current mood."""
    moods: list[MoodTag] = Field(..., min_length=1, max_length=3,
                                  description="1–3 mood tags selected by user")
    intensity: int = Field(5, ge=1, le=10,
                           description="Emotional intensity (1=low, 10=high)")


class MoodResponse(BaseModel):
    session_id: str
    moods: list[MoodTag]
    genre_weights: dict[str, float]  # mood → TMDB genre weight map


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
    """Normalized title record stored in Firestore and returned in recommendations."""
    id: str
    title: str
    media_type: MediaType
    platform: Optional[Platform] = None
    genres: list[str] = []
    mood_tags: list[MoodTag] = []
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    overview: Optional[str] = None
    release_year: Optional[int] = None
    rating: Optional[float] = None          # TMDB vote average
    mal_score: Optional[float] = None       # MyAnimeList score


class WatchEvent(BaseModel):
    """Single watch history entry parsed from an import file."""
    title: str
    platform: Platform
    watched_at: Optional[str] = None        # ISO date string
    episode: Optional[str] = None


# ── Recommendations ────────────────────────────────────────────────────────────

class RecommendationRequest(BaseModel):
    mood_session_id: str
    limit: int = Field(12, ge=1, le=50)
    exclude_watched: bool = True


class RecommendedTitle(Title):
    """Title enriched with recommendation metadata."""
    mood_score: float = Field(..., description="0–1 alignment with requested mood")
    cf_score: float   = Field(..., description="0–1 collaborative filtering score")
    final_score: float
    reason: str       = Field(..., description="Human-readable reason string shown in UI")


class RecommendationResponse(BaseModel):
    session_id: str
    moods: list[MoodTag]
    results: list[RecommendedTitle]
    serendipity_pick: Optional[RecommendedTitle] = None  # The wildcard suggestion


# ── Import ─────────────────────────────────────────────────────────────────────

class ImportResult(BaseModel):
    platform: Platform
    parsed_count: int
    new_titles: int
    skipped: int
    errors: list[str] = []


# ── User ──────────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    uid: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    favorite_genres: list[str] = []
    watch_count: int = 0
    onboarding_complete: bool = False


class FeedbackPayload(BaseModel):
    title_id: str
    session_id: str
    relevant: bool
    mood_matched: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
