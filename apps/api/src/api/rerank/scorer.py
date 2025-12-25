from __future__ import annotations

import math
from dataclasses import dataclass

from api.rerank.features import extract_year, parse_genres, parse_keywords, style_keywords


TONAL_GENRES: set[str] = {"comedy", "horror", "romance", "family"}


@dataclass(frozen=True)
class ScoringContext:
    genres: set[str]
    keywords: set[str]
    style: set[str]
    runtime: int | None
    year: int | None
    language: str | None


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def build_context(genres: str | None, keywords: str | None, runtime: int | None, release_date, language: str | None) -> ScoringContext:
    parsed_genres = parse_genres(genres)
    parsed_keywords = parse_keywords(keywords)
    return ScoringContext(
        genres=parsed_genres,
        keywords=parsed_keywords,
        style=style_keywords(parsed_keywords),
        runtime=runtime,
        year=extract_year(release_date),
        language=language.lower() if language else None,
    )


def score_candidate(
    anchor: ScoringContext,
    candidate: ScoringContext,
    distance: float,
    vote_count: int | None,
    max_vote_count: int,
) -> float:
    # Assumes `distance` is cosine distance from pgvector (<=>), which is typically in [0, 2].
    # Cosine similarity = 1 - distance, which can be in [-1, 1].
    # For ranking, negative similarities are usually not helpful, so clamp into [0, 1].
    sim = 1.0 - float(distance)
    sim = max(0.0, min(sim, 1.0))

    genre_jaccard = _jaccard(anchor.genres, candidate.genres)
    style_jaccard = _jaccard(anchor.style, candidate.style)

    runtime_penalty = 0.0
    if anchor.runtime is not None and candidate.runtime is not None:
        runtime_penalty = min(abs(anchor.runtime - candidate.runtime) / 120.0, 1.0)

    year_penalty = 0.0
    if anchor.year is not None and candidate.year is not None:
        year_penalty = min(abs(anchor.year - candidate.year) / 50.0, 1.0)

    lang_bonus = 0.0
    if anchor.language and candidate.language and anchor.language == candidate.language:
        lang_bonus = 1.0

    quality = 0.0
    if max_vote_count > 0 and vote_count:
        quality = math.log1p(vote_count) / math.log1p(max_vote_count)

    # Tonal genre mismatch penalty.
    anchor_tonal = anchor.genres & TONAL_GENRES
    candidate_tonal = candidate.genres & TONAL_GENRES
    mismatched = candidate_tonal - anchor_tonal
    tonal_penalty = min(len(mismatched), 2) / 2.0  # 0.0, 0.5, 1.0

    return (
        0.70 * sim
        + 0.15 * genre_jaccard
        + 0.10 * style_jaccard
        + 0.05 * quality
        + 0.03 * lang_bonus
        - 0.06 * tonal_penalty
        - 0.05 * runtime_penalty
        - 0.05 * year_penalty
    )


def rerank_candidates(anchor, candidates, top_n: int):
    max_vote_count = max((c.vote_count or 0) for c in candidates) if candidates else 0
    anchor_ctx = build_context(
        anchor.genres,
        anchor.keywords,
        anchor.runtime,
        anchor.release_date,
        anchor.original_language,
    )

    for candidate in candidates:
        candidate_ctx = build_context(
            candidate.genres,
            candidate.keywords,
            candidate.runtime,
            candidate.release_date,
            candidate.original_language,
        )
        candidate.score = score_candidate(
            anchor_ctx,
            candidate_ctx,
            candidate.distance,
            candidate.vote_count,
            max_vote_count,
        )

    candidates.sort(
        key=lambda item: (
            -(item.score or 0.0),
            item.distance,
            -(item.vote_count or 0),
        )
    )
    return candidates[:top_n]
