from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date

from pgvector.psycopg import Vector
from sqlalchemy import text

from api.config import (
    DISLIKE_MIN_COUNT,
    DISLIKE_WEIGHT,
    MAX_FETCH_CANDIDATES,
    MAX_SCORING_GENRES,
    MAX_SCORING_KEYWORDS,
    NEUTRAL_RATING_WEIGHT,
    RERANK_FETCH_MULTIPLIER,
    SCORING_CONTEXT_LIMIT,
    USER_UNWATCHED_COOLDOWN_DAYS,
)
from api.db import get_engine
from api.rerank.features import extract_year, parse_genres, parse_keywords, style_keywords
from api.rerank.scorer import ScoringContext, build_context, score_candidate


logger = logging.getLogger("api.recommendations")


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
    dislike_distance: float | None = None
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
    first_vec = rows[0][0]
    if first_vec is None:
        return None
    vector_len = len(first_vec)
    if vector_len == 0:
        return None
    totals = [0.0] * vector_len
    total_weight = 0.0
    for embedding, rating in rows:
        if embedding is None:
            continue
        weight = weight_fn(rating)
        if weight <= 0:
            continue
        total_weight += weight
        for idx, value in enumerate(embedding):
            totals[idx] += float(value) * weight
    if total_weight <= 0:
        return None
    return [value / total_weight for value in totals]


def _fetch_profile_embeddings(user_id: int):
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
        return conn.execute(q, {"user_id": user_id}).all()


def _fetch_disliked_embeddings(user_id: int):
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
    rows = _fetch_profile_embeddings(user_id)
    num_ratings = _count_watched_ratings(user_id)
    if not rows:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM user_profiles WHERE user_id = :user_id"), {"user_id": user_id})
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


def _fetch_scoring_rows(user_id: int, min_rating: int, max_rating: int) -> list[dict]:
    engine = get_engine()
    q = text(
        """
        SELECT m.genres,
               m.keywords,
               m.runtime,
               m.release_date,
               m.original_language,
               r.rating
        FROM user_movie_ratings r
        JOIN movies m ON m.id = r.movie_id
        WHERE r.user_id = :user_id
          AND r.status = 'watched'
          AND r.rating >= :min_rating
          AND r.rating <= :max_rating
        ORDER BY r.updated_at DESC
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        return [
            dict(row)
            for row in conn.execute(q, {"user_id": user_id, "min_rating": min_rating, "max_rating": max_rating, "limit": SCORING_CONTEXT_LIMIT}).mappings()
        ]


def _build_weighted_scoring_context(rows: list[dict], weight_fn) -> ScoringContext | None:
    if not rows:
        return None

    genre_counts = Counter()
    keyword_counts = Counter()
    language_counts = Counter()
    runtime_total = 0.0
    runtime_weight = 0.0
    year_total = 0.0
    year_weight = 0.0
    total_weight = 0.0

    for row in rows:
        weight = weight_fn(row.get("rating"))
        if weight <= 0:
            continue
        total_weight += weight

        for genre in parse_genres(row.get("genres")):
            genre_counts[genre] += weight
        for keyword in parse_keywords(row.get("keywords")):
            keyword_counts[keyword] += weight

        runtime = row.get("runtime")
        if runtime:
            runtime_total += float(runtime) * weight
            runtime_weight += weight

        year = extract_year(row.get("release_date"))
        if year:
            year_total += float(year) * weight
            year_weight += weight

        language = row.get("original_language")
        if language:
            language_counts[str(language).lower()] += weight

    if total_weight <= 0:
        return None

    top_genres = {g for g, _ in genre_counts.most_common(MAX_SCORING_GENRES)}
    top_keywords = {k for k, _ in keyword_counts.most_common(MAX_SCORING_KEYWORDS)}
    avg_runtime = int(runtime_total / runtime_weight) if runtime_weight else None
    avg_year = int(year_total / year_weight) if year_weight else None
    fav_lang = language_counts.most_common(1)[0][0] if language_counts else None

    return ScoringContext(
        genres=top_genres,
        keywords=top_keywords,
        style=style_keywords(top_keywords),
        runtime=avg_runtime,
        year=avg_year,
        language=fav_lang,
    )


def _build_user_scoring_context(user_id: int) -> ScoringContext | None:
    rows = _fetch_scoring_rows(user_id, min_rating=3, max_rating=5)
    return _build_weighted_scoring_context(rows, _profile_weight)


def _build_user_dislike_context(user_id: int) -> tuple[ScoringContext | None, int]:
    rows = _fetch_scoring_rows(user_id, min_rating=1, max_rating=2)
    return _build_weighted_scoring_context(rows, _dislike_weight), len(rows)


def get_recommendations(user_id: int, limit: int, offset: int = 0) -> list[Recommendation]:
    _ensure_user(user_id)
    engine = get_engine()
    q_profile = text("SELECT embedding AS embedding FROM user_profiles WHERE user_id = :user_id")
    with engine.begin() as conn:
        profile = conn.execute(q_profile, {"user_id": user_id}).first()
    if profile is None:
        return []

    embedding = profile[0]

    dislike_rows = _fetch_disliked_embeddings(user_id)
    dislike_embedding = None
    if len(dislike_rows) >= DISLIKE_MIN_COUNT:
        raw_dislike_embedding = _build_weighted_embedding(dislike_rows, _dislike_weight)
        if raw_dislike_embedding is not None:
            dislike_embedding = Vector(raw_dislike_embedding)

    dislike_ctx, dislike_ctx_count = _build_user_dislike_context(user_id)
    apply_dislike = (
        dislike_embedding is not None
        and dislike_ctx is not None
        and min(len(dislike_rows), dislike_ctx_count) >= DISLIKE_MIN_COUNT
    )

    # Fetch more candidates than needed to allow reranking to select the best matches.
    # The multiplier balances candidate diversity with query performance.
    # Fetch more candidates than needed to allow reranking to select the best matches.
    # The multiplier balances candidate diversity with query performance, but capped to prevent excessive load.
    fetch_limit = min(limit * RERANK_FETCH_MULTIPLIER, MAX_FETCH_CANDIDATES)

    # Build column list dynamically
    dislike_col = "(e.embedding <=> :dislike_embedding) AS dislike_distance" if apply_dislike else "NULL AS dislike_distance"

    q = text(
        f"""
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
               (e.embedding <=> :embedding) AS distance,
               {dislike_col}
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
    params = {
        "user_id": user_id,
        "embedding": embedding,
        "limit": fetch_limit,
        "offset": offset,
        "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
    }
    if apply_dislike:
        params["dislike_embedding"] = dislike_embedding

    with engine.begin() as conn:
        rows = conn.execute(q, params).mappings().all()

    candidates = [Recommendation(**row) for row in rows]
    if not candidates:
        return []

    user_ctx = _build_user_scoring_context(user_id)
    if not user_ctx:
        results = candidates[:limit]
        for item in results:
            item.similarity = 1.0 - item.distance
        return results

    max_vote_count = max((candidate.vote_count or 0) for candidate in candidates)
    like_scores: dict[int, float] = {}
    dislike_scores: dict[int, float] = {}

    # Scoring loop: processes up to RERANK_FETCH_MULTIPLIER * limit candidates.
    # For large limits, this could be expensive - monitor performance under load.

    for candidate in candidates:
        candidate_ctx = build_context(
            candidate.genres,
            candidate.keywords,
            candidate.runtime,
            candidate.release_date,
            candidate.original_language,
        )
        like_score = score_candidate(
            user_ctx,
            candidate_ctx,
            candidate.distance,
            candidate.vote_count,
            max_vote_count,
        )
        dislike_score = None
        if apply_dislike and candidate.dislike_distance is not None and dislike_ctx is not None:
            dislike_score = score_candidate(
                dislike_ctx,
                candidate_ctx,
                candidate.dislike_distance,
                candidate.vote_count,
                max_vote_count,
            )

        candidate.score = like_score - DISLIKE_WEIGHT * (dislike_score or 0.0)
        candidate.similarity = 1.0 - candidate.distance
        like_scores[candidate.id] = like_score
        if dislike_score is not None:
            dislike_scores[candidate.id] = dislike_score

    candidates.sort(
        key=lambda item: (
            -(item.score or 0.0),
            item.distance,
            -(item.vote_count or 0),
        )
    )
    results = candidates[:limit]
    if results:
        logger.info(
            "recommendation_rerank",
            extra={
                "user_id": user_id,
                "apply_dislike": apply_dislike,
                "dislike_count": dislike_ctx_count,
                "scores": [
                    {
                        "movie_id": item.id,
                        "score": round(item.score or 0.0, 4),
                        "like_score": round(like_scores.get(item.id, 0.0), 4),
                        "dislike_score": round(dislike_scores[item.id], 4) if item.id in dislike_scores else None,
                    }
                    for item in results
                ],
            },
        )
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
