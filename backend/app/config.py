"""
Configuration loaded from environment variables.
Copy `.env.example` to `.env` and fill in your values.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Firebase ───────────────────────────────────────────────────────────────
    # Path to your Firebase service account JSON file
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"

    # ── TMDB (movie metadata) ──────────────────────────────────────────────────
    TMDB_API_KEY: str = ""
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins; "*" for dev
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://moodflix.app"]

    # ── Recommendation Engine ──────────────────────────────────────────────────
    # How many candidates to generate before mood-reranking
    CF_CANDIDATE_POOL_SIZE: int = 50
    # Final number of recommendations returned to client
    FINAL_RECS_COUNT: int = 12

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
