from __future__ import annotations

from sqlalchemy import text

from api.db import get_engine
from api.users.db import ensure_user
from api.users.embeddings import (
    _build_weighted_embedding,
    _fetch_profile_embeddings,
    _profile_weight,
)
from api.users.ratings import _count_liked_ratings, _count_watched_ratings
from api.users.types import ProfileStats


def recompute_profile(user_id: int) -> None:
    ensure_user(user_id)
    rows = _fetch_profile_embeddings(user_id)
    num_ratings = _count_watched_ratings(user_id)
    if not rows:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM user_profiles WHERE user_id = :user_id"), {"user_id": user_id}
            )
        return

    averaged = _build_weighted_embedding(rows, _profile_weight)
    if averaged is None:
        return

    engine = get_engine()
    q = text(
        """
        INSERT INTO user_profiles (user_id, embedding, num_ratings, updated_at)
        VALUES (:user_id, :embedding, :num_ratings, now())
        ON CONFLICT (user_id)
        DO UPDATE SET embedding = EXCLUDED.embedding,
                      num_ratings = EXCLUDED.num_ratings,
                      updated_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(
            q,
            {
                "user_id": user_id,
                "embedding": averaged,
                "num_ratings": num_ratings,
            },
        )


def get_profile_stats(user_id: int) -> ProfileStats:
    ensure_user(user_id)
    engine = get_engine()
    q = text(
        """
        SELECT p.user_id,
               p.num_ratings,
               p.updated_at,
               p.embedding AS embedding
        FROM user_profiles p
        WHERE p.user_id = :user_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"user_id": user_id}).mappings().first()

    if not row:
        num_ratings = _count_watched_ratings(user_id)
        num_liked = _count_liked_ratings(user_id)
        return ProfileStats(
            user_id=user_id,
            num_ratings=num_ratings,
            num_liked=num_liked,
            embedding_norm=None,
            updated_at=None,
        )

    embedding = row["embedding"]
    norm = None
    if embedding is not None:
        norm = sum(float(value) ** 2 for value in embedding) ** 0.5

    num_liked = _count_liked_ratings(user_id)
    return ProfileStats(
        user_id=row["user_id"],
        num_ratings=row["num_ratings"],
        num_liked=num_liked,
        embedding_norm=norm,
        updated_at=str(row["updated_at"]) if row["updated_at"] else None,
    )
