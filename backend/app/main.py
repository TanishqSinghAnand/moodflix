"""
MoodFlix API - Mood-Aware Media Recommendation Engine
FastAPI backend designed to be consumed by both Web (Next.js) and Mobile (React Native) clients.

Architecture:
- RESTful JSON API with CORS support for all clients
- Firebase Firestore as primary database (scalable, real-time, no-ops)
- Modular router structure for clean separation of concerns
- JWT-based auth (Firebase Auth tokens verified server-side)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging

from app.routers import auth, users, mood, recommendations, import_history, onboarding, admin
from app.services.firebase import init_firebase
from app.config import settings

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, clean up on shutdown."""
    logger.info("Starting MoodFlix API...")
    init_firebase()
    logger.info("Firebase initialized.")
    yield
    logger.info("Shutting down MoodFlix API.")


app = FastAPI(
    title="MoodFlix API",
    description="Mood-aware media recommendation engine for movies, series & anime.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    # In production, replace "*" with your actual domains
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(auth.router,            prefix="/api/v1/auth",            tags=["Auth"])
app.include_router(users.router,           prefix="/api/v1/users",           tags=["Users"])
app.include_router(mood.router,            prefix="/api/v1/mood",            tags=["Mood"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(import_history.router,  prefix="/api/v1/import",          tags=["Import"])
app.include_router(onboarding.router,      prefix="/api/v1/onboarding",       tags=["Onboarding"])
app.include_router(admin.router,           prefix="/api/v1/admin",            tags=["Admin"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Simple liveness probe used by container orchestrators."""
    return {"status": "ok", "version": "1.0.0"}
