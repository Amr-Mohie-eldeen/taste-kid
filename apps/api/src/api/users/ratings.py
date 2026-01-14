from __future__ import annotations

from sqlalchemy import text

from api.db import get_engine
from api.users.db import _ensure_movie, _ensure_user
from api.users.types import RatedMovie


def upsert_rating(user_id: int, movie_id: int, rating: int | None, status: str) -> None:
    _ensure_user(user_id)
    _ensure_movie(movie_id)
    engine = get_engine()
    q = text(
        """
        INSERT INTO user_movie_ratings (user_id, movie_id, rating, status)
        VALUES (:user_id, :movie_id, :rating, :status)
        ON CONFLICT (user_id, movie_id)
        DO UPDATE SET rating = EXCLUDED.rating,
                      status = EXCLUDED.status,
                      updated_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(
            q,
            {
                "user_id": user_id,
                "movie_id": movie_id,
                "rating": rating,
                "status": status,
            },
        )


def _count_watched_ratings(user_id: int) -> int:
    engine = get_engine()
    q = text(
        """
        SELECT COUNT(*)
        FROM user_movie_ratings
        WHERE user_id = :user_id
          AND status = 'watched'
          AND rating IS NOT NULL
        """
    )
    with engine.begin() as conn:
        return int(conn.execute(q, {"user_id": user_id}).scalar() or 0)


def _count_liked_ratings(user_id: int) -> int:
    engine = get_engine()
    q = text(
        """
        SELECT COUNT(*)
        FROM user_movie_ratings
        WHERE user_id = :user_id
          AND status = 'watched'
          AND rating >= 4
        """
    )
    with engine.begin() as conn:
        return int(conn.execute(q, {"user_id": user_id}).scalar() or 0)


def get_user_ratings(user_id: int, limit: int, offset: int = 0) -> list[RatedMovie]:
    _ensure_user(user_id)
    engine = get_engine()
    q = text(
        """
        SELECT m.id,
               m.title,
               m.poster_path,
               m.backdrop_path,
               r.rating,
               r.status,
               r.updated_at
        FROM user_movie_ratings r
        JOIN movies m ON m.id = r.movie_id
        WHERE r.user_id = :user_id
        ORDER BY r.updated_at DESC NULLS LAST
        LIMIT :limit
        OFFSET :offset
        """
    )
    with engine.begin() as conn:
        rows = (
            conn.execute(q, {"user_id": user_id, "limit": limit, "offset": offset}).mappings().all()
        )
    return [
        RatedMovie(
            id=row["id"],
            title=row["title"],
            poster_path=row["poster_path"],
            backdrop_path=row["backdrop_path"],
            rating=row["rating"],
            status=row["status"],
            updated_at=str(row["updated_at"]) if row["updated_at"] else None,
        )
        for row in rows
    ]
