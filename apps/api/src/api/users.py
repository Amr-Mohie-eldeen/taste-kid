from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text

from api.config import USER_UNWATCHED_COOLDOWN_DAYS
from api.db import get_engine
from api.rerank.features import extract_year, parse_genres, parse_keywords, style_keywords
from api.rerank.scorer import ScoringContext, rerank_candidates


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
    keywords: str | None
    runtime: int | None
    original_language: str | None
    vote_count: int | None
    poster_path: str | None
    backdrop_path: str | None
    distance: float
    similarity: float | None = None
    score: float | None = None


@dataclass
class RatingQueueItem:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    poster_path: str | None
    backdrop_path: str | None


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
    poster_path: str | None
    backdrop_path: str | None
    source: str


@dataclass
class FeedItem:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    poster_path: str | None
    backdrop_path: str | None
    distance: float | None
    similarity: float | None
    score: float | None
    source: str


@dataclass
class UserMovieMatch:
    score: float | None


@dataclass
class RatedMovie:
    id: int
    title: str | None
    poster_path: str | None
    backdrop_path: str | None
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


def _build_user_scoring_context(user_id: int) -> ScoringContext | None:
    engine = get_engine()
    q = text(
        """
        SELECT m.genres, m.keywords, m.runtime, m.release_date, m.original_language
        FROM user_movie_ratings r
        JOIN movies m ON m.id = r.movie_id
        WHERE r.user_id = :user_id
          AND r.status = 'watched'
          AND r.rating >= 4
        ORDER BY r.updated_at DESC
        LIMIT 20
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(q, {"user_id": user_id}).mappings().all()

    if not rows:
        return None

    all_genres = []
    all_keywords = []
    runtimes = []
    years = []
    languages = []

    for row in rows:
        if row["genres"]:
            all_genres.extend([g.strip().lower() for g in row["genres"].split(",") if g.strip()])
        if row["keywords"]:
            all_keywords.extend([k.strip().lower() for k in row["keywords"].split(",") if k.strip()])
        if row["runtime"]:
            runtimes.append(row["runtime"])

        y = extract_year(row["release_date"])
        if y:
            years.append(y)
        if row["original_language"]:
            languages.append(row["original_language"].lower())

    top_genres = {g for g, _ in Counter(all_genres).most_common(5)}
    # Use more keywords for context to catch nuances
    top_keywords = {k for k, _ in Counter(all_keywords).most_common(20)}

    avg_runtime = int(sum(runtimes) / len(runtimes)) if runtimes else None
    avg_year = int(sum(years) / len(years)) if years else None
    fav_lang = Counter(languages).most_common(1)[0][0] if languages else None

    return ScoringContext(
        genres=top_genres,
        keywords=top_keywords,
        style=style_keywords(top_keywords),
        runtime=avg_runtime,
        year=avg_year,
        language=fav_lang,
    )


def get_recommendations(user_id: int, limit: int, offset: int = 0) -> list[Recommendation]:
    _ensure_user(user_id)
    engine = get_engine()
    q_profile = text("SELECT embedding AS embedding FROM user_profiles WHERE user_id = :user_id")
    with engine.begin() as conn:
        profile = conn.execute(q_profile, {"user_id": user_id}).first()
    if profile is None:
        return []

    embedding = profile[0]
    
    # Fetch more candidates for re-ranking
    fetch_limit = limit * 5
    
    q = text(
        """
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres,
               m.keywords,
               m.runtime,
               m.original_language,
               m.vote_count,
               m.poster_path,
               m.backdrop_path,
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
        OFFSET :offset
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(
            q,
            {
                "user_id": user_id,
                "embedding": embedding,
                "limit": fetch_limit,
                "offset": offset,
                "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
            },
        ).mappings().all()
    
    candidates = [Recommendation(**row) for row in rows]

    user_ctx = _build_user_scoring_context(user_id)
    if user_ctx:
        # Pass None as anchor because we provide anchor_context directly
        results = rerank_candidates(None, candidates, limit, anchor_context=user_ctx)
    else:
        results = candidates[:limit]

    for item in results:
        item.similarity = 1.0 - item.distance
    return results


def get_rating_queue(user_id: int, limit: int, offset: int = 0) -> list[RatingQueueItem]:
    _ensure_user(user_id)
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
        rows = conn.execute(
            q,
            {
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
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
               m.genres,
               m.poster_path,
               m.backdrop_path
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


def get_feed(user_id: int, limit: int, offset: int = 0) -> list[FeedItem]:
    _ensure_user(user_id)
    engine = get_engine()
    q_profile = text("SELECT 1 FROM user_profiles WHERE user_id = :user_id")
    with engine.begin() as conn:
        has_profile = conn.execute(q_profile, {"user_id": user_id}).first() is not None

    if has_profile:
        recs = get_recommendations(user_id, limit, offset)
        return [
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
        ]

    queue = get_rating_queue(user_id, limit, offset)
    return [
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
    ]


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
        rows = conn.execute(q, {"user_id": user_id, "limit": limit, "offset": offset}).mappings().all()
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
