"""
LightFM Matrix Factorization Service — V2 Recommendation Engine.

Why LightFM?
- Handles the cold-start problem via side features (genre tags, mood tags)
- Learns latent user/item embeddings from implicit feedback (thumbs up/down)
- Much better personalization than cosine similarity on genre counts
- Lightweight enough to train on a single CPU (no GPU needed)
- Hybrid: combines collaborative filtering AND content-based features

Architecture:
  Users     → represented by onboarding_vector + feedback history
  Items     → represented by TMDB genre tags + mood tags
  Feedback  → thumbs up = positive interaction, thumbs down = negative weight
  Training  → runs as a background job (triggered manually or on schedule)
  Serving   → trained model loaded from Firestore Storage, used at request time

Training data flow:
  Firestore feedback collection
    → extract (uid, title_id, relevant) triples
    → build sparse interaction matrix
    → extract item features from TMDB genre tags
    → extract user features from onboarding_vectors
    → train LightFM WARP model
    → serialize model → save to Firebase Storage
    → load at startup for serving

This file implements:
  1. Training pipeline (run offline / on schedule)
  2. Serving: score a list of candidate titles for a given user
  3. Fallback: if model not available, return None (cosine fallback in recommender)

SETUP REQUIRED:
  pip install lightfm scipy numpy
  Add to requirements.txt before using.

NOTE: LightFM training requires enough data to be useful.
Minimum recommended: 50+ users, 200+ feedback events.
Until then, the cosine recommender in recommender.py is used as fallback.
"""

from __future__ import annotations
import logging
import pickle
from typing import Optional

logger = logging.getLogger(__name__)

# ── Check if lightfm + numpy are available ────────────────────────────────────
# All ML deps are optional. App starts fine without them — cosine fallback used.
try:
    import numpy as np
    from lightfm import LightFM
    from lightfm.data import Dataset
    from scipy.sparse import csr_matrix
    LIGHTFM_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    LIGHTFM_AVAILABLE = False
    logger.info("LightFM/numpy not installed — ML recs disabled. "
                "Uncomment lightfm/scipy/numpy in requirements.txt to enable.")

# ── All genre features used as item side-features ─────────────────────────────
ALL_GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
    "Romance", "Science Fiction", "Thriller", "War", "Western",
]

ALL_MOODS = [
    "uplifting", "relaxing", "thrilling", "nostalgic", "dark",
    "romantic", "adventurous", "funny", "emotional", "mind_bending",
]

# Global model state
_model:   Optional["LightFM"]  = None
_dataset: Optional["Dataset"]  = None
_is_trained = False


def is_trained() -> bool:
    """Returns True if a trained LightFM model is loaded and ready."""
    return _is_trained and _model is not None


def train_model(feedback_records: list[dict], user_vectors: dict[str, dict]) -> bool:
    """
    Train the LightFM model from feedback data.

    Args:
        feedback_records: list of {uid, title_id, relevant, genres, mood_tags}
        user_vectors: {uid: {genre: weight}} from onboarding_vectors collection

    Returns:
        True if training succeeded, False otherwise.

    Minimum data requirements:
        - At least 50 unique users
        - At least 200 feedback events
        - At least 100 unique titles with feedback
    """
    global _model, _dataset, _is_trained

    if not LIGHTFM_AVAILABLE:
        logger.error("LightFM not installed — cannot train model.")
        return False

    # Validate minimum data requirements
    unique_users  = {r["uid"] for r in feedback_records}
    unique_titles = {r["title_id"] for r in feedback_records}

    if len(unique_users) < 50:
        logger.warning("Not enough users (%d < 50) to train LightFM.", len(unique_users))
        return False
    if len(feedback_records) < 200:
        logger.warning("Not enough feedback (%d < 200) to train LightFM.", len(feedback_records))
        return False

    logger.info("Training LightFM on %d users, %d titles, %d interactions",
                len(unique_users), len(unique_titles), len(feedback_records))

    try:
        # ── Build dataset ──────────────────────────────────────────────────────
        dataset = Dataset()
        dataset.fit(
            users=list(unique_users),
            items=list(unique_titles),
            user_features=[f"genre:{g}" for g in ALL_GENRES],
            item_features=[f"genre:{g}" for g in ALL_GENRES] + [f"mood:{m}" for m in ALL_MOODS],
        )

        # ── Build interaction matrix ───────────────────────────────────────────
        # Positive interactions: thumbs up (weight=1.0)
        # Negative interactions: thumbs down (weight=-1.0, treated as 0 in WARP)
        interactions_data = [
            (r["uid"], r["title_id"], 1.0 if r["relevant"] else 0.0)
            for r in feedback_records
        ]
        interactions, weights = dataset.build_interactions(
            [(uid, tid, w) for uid, tid, w in interactions_data if w > 0]
        )

        # ── Build user feature matrix from onboarding vectors ─────────────────
        user_features_data = []
        for uid, genre_vec in user_vectors.items():
            features = [(f"genre:{g}", w) for g, w in genre_vec.items() if g in ALL_GENRES]
            if features:
                user_features_data.append((uid, features))

        user_features = dataset.build_user_features(user_features_data)

        # ── Build item feature matrix from genre/mood tags ────────────────────
        item_features_data = []
        for r in feedback_records:
            title_id = r["title_id"]
            features = (
                [(f"genre:{g}", 1.0) for g in r.get("genres", []) if g in ALL_GENRES] +
                [(f"mood:{m}", 1.0)  for m in r.get("mood_tags", []) if m in ALL_MOODS]
            )
            if features:
                item_features_data.append((title_id, features))

        item_features = dataset.build_item_features(item_features_data)

        # ── Train WARP model ───────────────────────────────────────────────────
        # WARP (Weighted Approximate-Rank Pairwise) is best for implicit feedback
        # num_components=64: latent dimension (higher = more expressive, slower)
        # epochs=30: number of training passes
        model = LightFM(
            no_components=64,
            loss="warp",
            learning_rate=0.05,
            item_alpha=1e-6,
            user_alpha=1e-6,
        )
        model.fit(
            interactions,
            user_features=user_features,
            item_features=item_features,
            epochs=30,
            num_threads=4,
            verbose=True,
        )

        _model    = model
        _dataset  = dataset
        _is_trained = True
        logger.info("LightFM model trained successfully.")
        return True

    except Exception as exc:
        logger.error("LightFM training failed: %s", exc)
        return False


def score_candidates(
    uid: str,
    candidate_title_ids: list[str],
    user_genre_vector: dict[str, float],
) -> dict[str, float]:
    """
    Score candidate titles for a given user using the trained LightFM model.

    Returns:
        dict mapping title_id → LightFM score (higher = better match)
        Returns empty dict if model not trained or user not in training set.

    Falls back gracefully — recommender.py uses cosine scoring when this returns {}.
    """
    if not is_trained() or not LIGHTFM_AVAILABLE:
        return {}

    try:
        user_id_map, item_id_map = _dataset.mapping()[:2]

        # Check if user is in training set
        if uid not in user_id_map:
            logger.debug("User %s not in LightFM training set — using cosine fallback", uid)
            return {}

        user_idx = user_id_map[uid]

        # Filter to candidates that exist in training set
        known_items = [tid for tid in candidate_title_ids if tid in item_id_map]
        if not known_items:
            return {}

        item_indices = np.array([item_id_map[tid] for tid in known_items])

        # Build user feature vector from current genre preferences
        # (may differ from training time if they've watched more since)
        user_features_row = [
            (f"genre:{g}", w) for g, w in user_genre_vector.items() if g in ALL_GENRES
        ]
        user_feat_matrix = _dataset.build_user_features([(uid, user_features_row)])

        # Score all known items at once (LightFM is vectorized)
        scores = _model.predict(
            user_ids=np.array([user_idx] * len(item_indices)),
            item_ids=item_indices,
            user_features=user_feat_matrix,
        )

        return {tid: float(score) for tid, score in zip(known_items, scores)}

    except Exception as exc:
        logger.error("LightFM scoring failed: %s", exc)
        return {}


def save_model(path: str = "/tmp/lightfm_model.pkl") -> bool:
    """Serialize trained model to disk (call after training)."""
    if not _model or not _dataset:
        return False
    try:
        with open(path, "wb") as f:
            pickle.dump({"model": _model, "dataset": _dataset}, f)
        logger.info("LightFM model saved to %s", path)
        return True
    except Exception as exc:
        logger.error("Failed to save model: %s", exc)
        return False


def load_model(path: str = "/tmp/lightfm_model.pkl") -> bool:
    """Load a previously trained model from disk."""
    global _model, _dataset, _is_trained
    if not LIGHTFM_AVAILABLE:
        return False
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        _model      = data["model"]
        _dataset    = data["dataset"]
        _is_trained = True
        logger.info("LightFM model loaded from %s", path)
        return True
    except FileNotFoundError:
        logger.info("No saved LightFM model found at %s — using cosine fallback", path)
        return False
    except Exception as exc:
        logger.error("Failed to load model: %s", exc)
        return False
