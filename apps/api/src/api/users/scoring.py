from __future__ import annotations

from collections import Counter

from sqlalchemy import text

from api.config import MAX_SCORING_GENRES, MAX_SCORING_KEYWORDS, SCORING_CONTEXT_LIMIT
from api.db import get_engine
from api.rerank.features import extract_year, parse_genres, parse_keywords, style_keywords
from api.rerank.scorer import ScoringContext
from api.users.embeddings import _dislike_weight, _profile_weight


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
            for row in conn.execute(
                q,
                {
                    "user_id": user_id,
                    "min_rating": min_rating,
                    "max_rating": max_rating,
                    "limit": SCORING_CONTEXT_LIMIT,
                },
            ).mappings()
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
