from __future__ import annotations

import logging
import time
import uuid

from pgvector.psycopg import Vector
from sqlalchemy import text

from api.config import (
    DISLIKE_MIN_COUNT,
    DISLIKE_WEIGHT,
    MAX_FETCH_CANDIDATES,
    RECOMMENDATIONS_CACHE_MAX_WINDOWS_PER_REQUEST,
    RECOMMENDATIONS_CACHE_TTL_S,
    USER_UNWATCHED_COOLDOWN_DAYS,
)


def _paginate_windows(
    *,
    items: list[Recommendation],
    cursor: int,
    page_size: int,
    window_size: int,
) -> tuple[list[Recommendation], dict[str, object]]:
    if cursor >= len(items):
        return [], {"next_cursor": None, "has_more": False}

    window_index = cursor // window_size
    window_end = min((window_index + 1) * window_size, len(items))
    page_end = min(cursor + page_size, window_end)

    page_items = items[cursor:page_end]

    if page_end < window_end:
        return page_items, {"next_cursor": str(page_end), "has_more": True}

    next_window_start = (window_index + 1) * window_size
    return page_items, {"next_cursor": str(next_window_start), "has_more": True}
from api.db import get_engine
from api.rerank.scorer import build_context, score_candidate
from api.users.db import ensure_user
from api.users.embeddings import (
    _build_weighted_embedding,
    _dislike_weight,
    _fetch_disliked_embeddings,
)
from api.users.feed_cache import FeedCacheEntry, _CACHE
from api.users.scoring import _build_user_dislike_context, _build_user_scoring_context
from api.users.types import Recommendation

logger = logging.getLogger("api")


def _recommendation_cache_key(user_id: int) -> str:
    return f"recs:{user_id}"


def invalidate_recommendations_cache(user_id: int) -> None:
    _CACHE.delete(_recommendation_cache_key(user_id))


def _fetch_recommendation_window(
    *,
    user_id: int,
    embedding,
    dislike_embedding: Vector | None,
    apply_dislike: bool,
    window_size: int,
    window_index: int,
) -> list[Recommendation]:
    engine = get_engine()

    if apply_dislike:
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
                   (e.embedding <=> :embedding) AS distance,
                   (e.embedding <=> :dislike_embedding) AS dislike_distance
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
        params: dict[str, object] = {
            "user_id": user_id,
            "embedding": embedding,
            "dislike_embedding": dislike_embedding,
            "limit": window_size,
            "offset": window_index * window_size,
            "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
        }
    else:
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
                   (e.embedding <=> :embedding) AS distance,
                   NULL AS dislike_distance
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
            "limit": window_size,
            "offset": window_index * window_size,
            "cooldown_days": USER_UNWATCHED_COOLDOWN_DAYS,
        }

    with engine.begin() as conn:
        rows = conn.execute(q, params).mappings().all()

    return [Recommendation(**row) for row in rows]


def _rerank_candidates(
    *,
    user_id: int,
    candidates: list[Recommendation],
    apply_dislike: bool,
    dislike_ctx,
    dislike_ctx_count: int,
) -> tuple[list[Recommendation], dict[int, float], dict[int, float]]:
    user_ctx = _build_user_scoring_context(user_id)
    if not user_ctx:
        for item in candidates:
            item.similarity = 1.0 - item.distance
        return candidates, {}, {}

    max_vote_count = max((candidate.vote_count or 0) for candidate in candidates) if candidates else 0
    like_scores: dict[int, float] = {}
    dislike_scores: dict[int, float] = {}

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
    return candidates, like_scores, dislike_scores


def get_recommendations_page(
    user_id: int, page_size: int, cursor: int
) -> tuple[list[Recommendation], dict[str, object]]:
    ensure_user(user_id)

    engine = get_engine()
    q_profile = text("SELECT embedding AS embedding FROM user_profiles WHERE user_id = :user_id")
    with engine.begin() as conn:
        profile = conn.execute(q_profile, {"user_id": user_id}).first()
    if profile is None:
        return [], {"next_cursor": None, "has_more": False}

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

    window_size = MAX_FETCH_CANDIDATES
    window_index = cursor // window_size

    cache_key = _recommendation_cache_key(user_id)
    cached = _CACHE.get(cache_key)
    cached_items: list[Recommendation] = list(cached.items) if cached is not None else []

    needed_end = (window_index + 1) * window_size
    if len(cached_items) < needed_end and RECOMMENDATIONS_CACHE_TTL_S > 0:
        missing_windows_start = len(cached_items) // window_size
        max_windows = max(1, RECOMMENDATIONS_CACHE_MAX_WINDOWS_PER_REQUEST)
        for idx in range(missing_windows_start, missing_windows_start + max_windows):
            window_candidates = _fetch_recommendation_window(
                user_id=user_id,
                embedding=embedding,
                dislike_embedding=dislike_embedding,
                apply_dislike=apply_dislike,
                window_size=window_size,
                window_index=idx,
            )
            if not window_candidates:
                break

            reranked, _like, _dislike = _rerank_candidates(
                user_id=user_id,
                candidates=window_candidates,
                apply_dislike=apply_dislike,
                dislike_ctx=dislike_ctx,
                dislike_ctx_count=dislike_ctx_count,
            )
            cached_items.extend(reranked)
            if len(window_candidates) < window_size:
                break

        now = time.time()
        entry = FeedCacheEntry(
            feed_id=str(uuid.uuid4()),
            expires_at=now + RECOMMENDATIONS_CACHE_TTL_S,
            items=cached_items,
        )
        _CACHE.set(cache_key, entry)

    items, meta = _paginate_windows(
        items=cached_items,
        cursor=cursor,
        page_size=page_size,
        window_size=window_size,
    )

    if items:
        logger.info(
            "recommendation_page",
            extra={
                "user_id": user_id,
                "apply_dislike": apply_dislike,
                "dislike_count": dislike_ctx_count,
                "cursor": cursor,
                "page_size": page_size,
                "window_size": window_size,
                "returned": len(items),
            },
        )

    return items, meta


def get_recommendations(user_id: int, limit: int, offset: int = 0) -> list[Recommendation]:
    items, _meta = get_recommendations_page(user_id, limit, offset)
    return items
