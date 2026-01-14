from __future__ import annotations

import logging

from pgvector.psycopg import Vector
from sqlalchemy import text

from api.config import (
    DISLIKE_MIN_COUNT,
    DISLIKE_WEIGHT,
    MAX_FETCH_CANDIDATES,
    RERANK_FETCH_MULTIPLIER,
    USER_UNWATCHED_COOLDOWN_DAYS,
)
from api.db import get_engine
from api.rerank.scorer import build_context, score_candidate
from api.users.db import ensure_user
from api.users.embeddings import (
    _build_weighted_embedding,
    _dislike_weight,
    _fetch_disliked_embeddings,
)
from api.users.scoring import _build_user_dislike_context, _build_user_scoring_context
from api.users.types import Recommendation

logger = logging.getLogger("api")


def get_recommendations(user_id: int, limit: int, offset: int = 0) -> list[Recommendation]:
    ensure_user(user_id)
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
    # The multiplier balances candidate diversity with query performance, but capped to prevent excessive load.
    fetch_limit = min(limit * RERANK_FETCH_MULTIPLIER, MAX_FETCH_CANDIDATES)

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
    params: dict[str, object] = {
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
        log_sample = results[:10]
        logger.info(
            "recommendation_rerank",
            extra={
                "user_id": user_id,
                "apply_dislike": apply_dislike,
                "dislike_count": dislike_ctx_count,
                "result_count": len(results),
                "scores": [
                    {
                        "movie_id": item.id,
                        "score": round(item.score or 0.0, 4),
                        "like_score": round(like_scores.get(item.id, 0.0), 4),
                        "dislike_score": round(dislike_scores[item.id], 4)
                        if item.id in dislike_scores
                        else None,
                    }
                    for item in log_sample
                ],
            },
        )
    return results
