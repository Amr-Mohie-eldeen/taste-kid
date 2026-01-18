from __future__ import annotations

from sqlalchemy import text

from api.config import USER_UNWATCHED_COOLDOWN_DAYS
from api.db import get_engine
from api.users.db import ensure_user
from api.users.recommendations import get_recommendations_page
from api.users.types import FeedItem, NextMovie, RatingQueueItem


def get_rating_queue(user_id: int, limit: int, offset: int = 0) -> list[RatingQueueItem]:
    if user_id != 0:
        ensure_user(user_id)
    engine = get_engine()
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres,
               m.poster_path,
               m.backdrop_path
        FROM movies m
        LEFT JOIN user_movie_ratings r
          ON r.movie_id = m.id
         AND r.user_id = :user_id
        WHERE r.movie_id IS NULL
           OR (r.status = 'unwatched' AND r.updated_at < now() - make_interval(days => :cooldown_days))
        ORDER BY m.vote_count DESC NULLS LAST
        LIMIT :limit
        OFFSET :offset
        """
    )
    with engine.begin() as conn:
        rows = (
            conn.execute(
                q,
                {
                    "user_id": user_id,
                    "limit": limit,
                    "offset": offset,
                    "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
                },
            )
            .mappings()
            .all()
        )
    return [RatingQueueItem(**row) for row in rows]


def _get_next_from_recs(user_id: int) -> NextMovie | None:
    engine = get_engine()
    q_embedding = text("SELECT embedding FROM user_profiles WHERE user_id = :user_id")
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres,
               m.poster_path,
               m.backdrop_path
        FROM movie_embeddings e
        JOIN movies m ON m.id = e.movie_id
        LEFT JOIN user_movie_ratings r
          ON r.movie_id = m.id
         AND r.user_id = :user_id
        WHERE r.movie_id IS NULL
           OR (r.status = 'unwatched' AND r.updated_at < now() - make_interval(days => :cooldown_days))
        ORDER BY e.embedding <=> :embedding
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        embedding = conn.execute(q_embedding, {"user_id": user_id}).scalar()
        if embedding is None:
            return None

        row = (
            conn.execute(
                q,
                {
                    "user_id": user_id,
                    "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
                    "embedding": embedding,
                },
            )
            .mappings()
            .first()
        )

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
               m.genres,
               m.poster_path,
               m.backdrop_path
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
        row = (
            conn.execute(
                q,
                {
                    "user_id": user_id,
                    "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
                },
            )
            .mappings()
            .first()
        )
    if not row:
        return None
    return NextMovie(source="popularity", **row)


def get_next_movie(user_id: int) -> NextMovie | None:
    ensure_user(user_id)
    next_movie = _get_next_from_recs(user_id)
    if next_movie:
        return next_movie
    return _get_next_from_popularity(user_id)


def get_feed(
    user_id: int, limit: int, offset: int = 0
) -> tuple[list[FeedItem], dict[str, object] | None]:
    ensure_user(user_id)
    engine = get_engine()
    q_profile = text("SELECT 1 FROM user_profiles WHERE user_id = :user_id")
    with engine.begin() as conn:
        has_profile = conn.execute(q_profile, {"user_id": user_id}).first() is not None

    if has_profile:
        recs, meta = get_recommendations_page(user_id, limit, offset)
        return (
            [
                FeedItem(
                    id=item.id,
                    title=item.title,
                    release_date=item.release_date,
                    genres=item.genres,
                    poster_path=item.poster_path,
                    backdrop_path=item.backdrop_path,
                    distance=item.distance,
                    similarity=item.similarity,
                    score=item.score,
                    source="profile",
                )
                for item in recs
            ],
            meta,
        )

    queue = get_rating_queue(user_id, limit, offset)
    return (
        [
            FeedItem(
                id=item.id,
                title=item.title,
                release_date=item.release_date,
                genres=item.genres,
                poster_path=item.poster_path,
                backdrop_path=item.backdrop_path,
                distance=None,
                similarity=None,
                score=None,
                source="popularity",
            )
            for item in queue
        ],
        None,
    )
