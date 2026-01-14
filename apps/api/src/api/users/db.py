from __future__ import annotations

from sqlalchemy import text

from api.db import get_engine
from api.users.types import MovieNotFoundError, UserNotFoundError, UserSummary


def ensure_user(user_id: int) -> None:
    engine = get_engine()
    q = text("SELECT 1 FROM users WHERE id = :user_id")
    with engine.begin() as conn:
        row = conn.execute(q, {"user_id": user_id}).first()
    if row is None:
        raise UserNotFoundError(f"User {user_id} not found")


def ensure_movie(movie_id: int) -> None:
    engine = get_engine()
    q = text("SELECT 1 FROM movies WHERE id = :movie_id")
    with engine.begin() as conn:
        row = conn.execute(q, {"movie_id": movie_id}).first()
    if row is None:
        raise MovieNotFoundError(f"Movie {movie_id} not found")


def create_user(display_name: str | None = None) -> int:
    engine = get_engine()
    q = text("INSERT INTO users (display_name) VALUES (:display_name) RETURNING id")
    with engine.begin() as conn:
        row = conn.execute(q, {"display_name": display_name}).first()
    if row is None:
        raise RuntimeError("Failed to create user")
    return int(row[0])


def get_user_summary(user_id: int) -> UserSummary:
    engine = get_engine()
    q = text(
        """
        SELECT u.id,
               u.display_name,
               COALESCE(p.num_ratings, 0) AS num_ratings,
               p.updated_at AS profile_updated_at
        FROM users u
        LEFT JOIN user_profiles p ON p.user_id = u.id
        WHERE u.id = :user_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"user_id": user_id}).mappings().first()
    if not row:
        raise UserNotFoundError(f"User {user_id} not found")
    return UserSummary(
        id=row["id"],
        display_name=row["display_name"],
        num_ratings=row["num_ratings"],
        profile_updated_at=str(row["profile_updated_at"]) if row["profile_updated_at"] else None,
    )
