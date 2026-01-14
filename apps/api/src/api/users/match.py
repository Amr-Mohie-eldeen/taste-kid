from __future__ import annotations

from sqlalchemy import text

from api.db import get_engine
from api.users.db import _ensure_movie, _ensure_user
from api.users.types import UserMovieMatch


def get_user_movie_match(user_id: int, movie_id: int) -> UserMovieMatch:
    _ensure_user(user_id)
    _ensure_movie(movie_id)
    engine = get_engine()
    q = text(
        """
        SELECT (e.embedding <=> p.embedding) AS distance
        FROM user_profiles p
        LEFT JOIN movie_embeddings e ON e.movie_id = :movie_id
        WHERE p.user_id = :user_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"user_id": user_id, "movie_id": movie_id}).first()
    if not row or row[0] is None:
        return UserMovieMatch(score=None)
    distance = float(row[0])
    similarity = 1.0 - distance
    score = round(min(100.0, max(0.0, similarity * 100)), 2)
    return UserMovieMatch(score=score)
