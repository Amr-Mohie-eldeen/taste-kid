from __future__ import annotations

from sqlalchemy import text

from api.config import NEUTRAL_RATING_WEIGHT
from api.db import get_engine


def _profile_weight(rating: int | None) -> float:
    if rating is None:
        return 0.0
    if rating < 3:
        return 0.0  # Profile weights only apply to ratings >= 3
    if rating == 3:
        return NEUTRAL_RATING_WEIGHT
    return max(0.0, float(rating) / 5.0)


def _dislike_weight(rating: int | None) -> float:
    if rating is None or rating > 2:
        return 0.0
    return 1.0 if rating <= 1 else 0.5


def _build_weighted_embedding(rows, weight_fn) -> list[float] | None:
    if not rows:
        return None

    # Find the first non-None embedding to determine vector length
    vector_len = None
    for embedding, _ in rows:
        if embedding is not None:
            vector_len = len(embedding)
            if vector_len == 0:
                return None
            break

    if vector_len is None:
        return None

    totals = [0.0] * vector_len
    total_weight = 0.0

    for embedding, rating in rows:
        if embedding is None:
            continue
        if len(embedding) != vector_len:
            continue  # Skip embeddings with mismatched lengths
        weight = weight_fn(rating)
        if weight <= 0:
            continue
        total_weight += weight
        for idx, value in enumerate(embedding):
            totals[idx] += float(value) * weight

    if total_weight <= 0:
        return None
    return [value / total_weight for value in totals]


def _fetch_profile_embeddings(user_id: int) -> list:
    engine = get_engine()
    q = text(
        """
        SELECT e.embedding AS embedding,
               r.rating
        FROM user_movie_ratings r
        JOIN movie_embeddings e ON e.movie_id = r.movie_id
        WHERE r.user_id = :user_id
          AND r.status = 'watched'
          AND r.rating >= 3
        """
    )
    with engine.begin() as conn:
        return list(conn.execute(q, {"user_id": user_id}).all())


def _fetch_disliked_embeddings(user_id: int) -> list:
    engine = get_engine()
    q = text(
        """
        SELECT e.embedding AS embedding,
               r.rating
        FROM user_movie_ratings r
        JOIN movie_embeddings e ON e.movie_id = r.movie_id
        WHERE r.user_id = :user_id
          AND r.status = 'watched'
          AND r.rating <= 2
        """
    )
    with engine.begin() as conn:
        return list(conn.execute(q, {"user_id": user_id}).all())
