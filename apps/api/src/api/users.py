from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text

from api.config import USER_UNWATCHED_COOLDOWN_DAYS
from api.db import get_engine


class UserNotFoundError(LookupError):
    pass


class MovieNotFoundError(LookupError):
    pass


@dataclass
class UserSummary:
    id: int
    display_name: str | None
    num_ratings: int
    profile_updated_at: str | None


@dataclass
class Recommendation:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    distance: float
    similarity: float | None = None


@dataclass
class RatingQueueItem:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None


@dataclass
class ProfileStats:
    user_id: int
    num_ratings: int
    num_liked: int
    embedding_norm: float | None
    updated_at: str | None


@dataclass
class NextMovie:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    source: str


@dataclass
class RatedMovie:
    id: int
    title: str | None
    rating: int | None
    status: str
    updated_at: str | None


def _ensure_user(user_id: int) -> None:
    engine = get_engine()
    q = text("SELECT 1 FROM users WHERE id = :user_id")
    with engine.begin() as conn:
        row = conn.execute(q, {"user_id": user_id}).first()
    if row is None:
        raise UserNotFoundError(f"User {user_id} not found")


def _ensure_movie(movie_id: int) -> None:
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


def _fetch_liked_embeddings(user_id: int):
    engine = get_engine()
    q = text(
        """
        SELECT e.embedding AS embedding,
               r.rating
        FROM user_movie_ratings r
        JOIN movie_embeddings e ON e.movie_id = r.movie_id
        WHERE r.user_id = :user_id
          AND r.status = 'watched'
          AND r.rating >= 4
        """
    )
    with engine.begin() as conn:
        return conn.execute(q, {"user_id": user_id}).all()


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




def recompute_profile(user_id: int) -> None:
    _ensure_user(user_id)
    rows = _fetch_liked_embeddings(user_id)
    num_ratings = _count_watched_ratings(user_id)
    if not rows:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM user_profiles WHERE user_id = :user_id"), {"user_id": user_id})
        return

    first_vec = rows[0][0]
    if first_vec is None:
        return
    vector_len = len(first_vec)
    if vector_len == 0:
        return
    totals = [0.0] * vector_len
    total_weight = 0.0
    for embedding, rating in rows:
        weight = (rating or 0) / 5.0
        if weight <= 0:
            continue
        total_weight += weight
        for idx, value in enumerate(embedding):
            totals[idx] += float(value) * weight

    if total_weight <= 0:
        return

    averaged = [value / total_weight for value in totals]
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


def get_recommendations(user_id: int, limit: int) -> list[Recommendation]:
    _ensure_user(user_id)
    engine = get_engine()
    q_profile = text("SELECT embedding AS embedding FROM user_profiles WHERE user_id = :user_id")
    with engine.begin() as conn:
        profile = conn.execute(q_profile, {"user_id": user_id}).first()
    if profile is None:
        return []

    embedding = profile[0]
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres,
               (e.embedding <=> :embedding) AS distance
        FROM movie_embeddings e
        JOIN movies m ON m.id = e.movie_id
        LEFT JOIN user_movie_ratings r
          ON r.movie_id = m.id
         AND r.user_id = :user_id
        WHERE r.movie_id IS NULL
           OR (r.status = 'unwatched' AND r.updated_at < now() - make_interval(days => :cooldown_days))
        ORDER BY e.embedding <=> :embedding
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(
            q,
            {
                "user_id": user_id,
                "embedding": embedding,
                "limit": limit,
                "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
            },
        ).mappings().all()
    results = [Recommendation(**row) for row in rows]
    for item in results:
        item.similarity = 1.0 - item.distance
    return results


def get_rating_queue(user_id: int, limit: int) -> list[RatingQueueItem]:
    _ensure_user(user_id)
    engine = get_engine()
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres
        FROM movies m
        LEFT JOIN user_movie_ratings r
          ON r.movie_id = m.id
         AND r.user_id = :user_id
        WHERE r.movie_id IS NULL
           OR (r.status = 'unwatched' AND r.updated_at < now() - make_interval(days => :cooldown_days))
        ORDER BY m.vote_count DESC NULLS LAST
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(
            q,
            {
                "user_id": user_id,
                "limit": limit,
                "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
            },
        ).mappings().all()
    return [RatingQueueItem(**row) for row in rows]


def _get_next_from_recs(user_id: int) -> NextMovie | None:
    engine = get_engine()
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres
        FROM user_profiles p
        JOIN movie_embeddings e ON TRUE
        JOIN movies m ON m.id = e.movie_id
        LEFT JOIN user_movie_ratings r
          ON r.movie_id = m.id
         AND r.user_id = :user_id
        WHERE p.user_id = :user_id
          AND (
            r.movie_id IS NULL
            OR (r.status = 'unwatched' AND r.updated_at < now() - make_interval(days => :cooldown_days))
          )
        ORDER BY e.embedding <=> p.embedding
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            q,
            {
                "user_id": user_id,
                "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
            },
        ).mappings().first()
    if not row:
        return None
    return NextMovie(source="profile", **row)


def _get_next_from_popularity(user_id: int) -> NextMovie | None:
    engine = get_engine()
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres
        FROM movies m
        LEFT JOIN user_movie_ratings r
          ON r.movie_id = m.id
         AND r.user_id = :user_id
        WHERE r.movie_id IS NULL
           OR (r.status = 'unwatched' AND r.updated_at < now() - make_interval(days => :cooldown_days))
        ORDER BY m.vote_count DESC NULLS LAST
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            q,
            {
                "user_id": user_id,
                "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
            },
        ).mappings().first()
    if not row:
        return None
    return NextMovie(source="popularity", **row)


def get_next_movie(user_id: int) -> NextMovie | None:
    _ensure_user(user_id)
    next_movie = _get_next_from_recs(user_id)
    if next_movie:
        return next_movie
    return _get_next_from_popularity(user_id)


def get_user_ratings(user_id: int, limit: int) -> list[RatedMovie]:
    _ensure_user(user_id)
    engine = get_engine()
    q = text(
        """
        SELECT m.id,
               m.title,
               r.rating,
               r.status,
               r.updated_at
        FROM user_movie_ratings r
        JOIN movies m ON m.id = r.movie_id
        WHERE r.user_id = :user_id
        ORDER BY r.updated_at DESC NULLS LAST
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(q, {"user_id": user_id, "limit": limit}).mappings().all()
    return [
        RatedMovie(
            id=row["id"],
            title=row["title"],
            rating=row["rating"],
            status=row["status"],
            updated_at=str(row["updated_at"]) if row["updated_at"] else None,
        )
        for row in rows
    ]


def get_profile_stats(user_id: int) -> ProfileStats:
    _ensure_user(user_id)
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
