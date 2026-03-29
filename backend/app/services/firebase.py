"""
Firebase Admin SDK initializer.

Why Firebase?
- Firestore scales horizontally out of the box (no DBA needed)
- Firebase Auth handles JWT verification, OAuth, magic links
- Real-time listeners enable future live features (watch parties, etc.)
- Same SDK works for the planned React Native app (firebase-admin on server,
  @react-native-firebase on client)
- Free tier is generous; pricing scales linearly with usage
"""

import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import lru_cache
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_db: firestore.Client | None = None


def init_firebase() -> None:
    """Initialize Firebase Admin SDK. Safe to call multiple times (idempotent)."""
    global _db
    if firebase_admin._apps:
        return

    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    logger.info("Firebase Admin SDK initialized.")


def get_db() -> firestore.Client:
    """Return the Firestore client (singleton)."""
    if _db is None:
        raise RuntimeError("Firebase not initialized. Call init_firebase() first.")
    return _db


def verify_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.
    Raises firebase_admin.auth.InvalidIdTokenError on failure.
    """
    return auth.verify_id_token(id_token)
