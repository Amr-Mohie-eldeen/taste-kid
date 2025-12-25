from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy import text

from api.db import get_engine
from api.rerank.scorer import rerank_candidates


class EmbeddingNotFoundError(LookupError):
    pass


@dataclass
class MovieMetadata:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    keywords: str | None
    runtime: int | None
    original_language: str | None
    vote_count: int | None
    vote_average: float | None


@dataclass
class Candidate(MovieMetadata):
    distance: float
    score: float | None = None


def fetch_movie_metadata(movie_id: int) -> MovieMetadata | None:
    engine = get_engine()
    q = text(
        """
        SELECT id,
               title,
               release_date,
               genres,
               keywords,
               runtime,
               original_language,
               vote_count,
               vote_average
        FROM movies
        WHERE id = :movie_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"movie_id": movie_id}).mappings().first()
    if not row:
        return None
    return MovieMetadata(**row)


def find_movie_id_by_title(title: str) -> MovieMetadata | None:
    engine = get_engine()
    like_title = f"%{title}%"
    q = text(
        """
        SELECT id,
               title,
               release_date,
               genres,
               keywords,
               runtime,
               original_language,
               vote_count,
               vote_average
        FROM movies
        WHERE lower(title) = lower(:title)
           OR lower(original_title) = lower(:title)
           OR title ILIKE :like_title
           OR original_title ILIKE :like_title
        ORDER BY
            CASE
                WHEN lower(title) = lower(:title) THEN 0
                WHEN lower(original_title) = lower(:title) THEN 1
                ELSE 2
            END,
            vote_count DESC NULLS LAST
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"title": title, "like_title": like_title}).mappings().first()
    if not row:
        return None
    return MovieMetadata(**row)


def _ensure_embedding(movie_id: int) -> None:
    engine = get_engine()
    q = text("SELECT 1 FROM movie_embeddings WHERE movie_id = :movie_id")
    with engine.begin() as conn:
        row = conn.execute(q, {"movie_id": movie_id}).first()
    if row is None:
        raise EmbeddingNotFoundError(f"No embedding for movie_id={movie_id}")


def get_similar_candidates(movie_id: int, k: int = 200) -> list[Candidate]:
    _ensure_embedding(movie_id)
    engine = get_engine()
    q = text(
        """
        WITH q AS (
            SELECT embedding
            FROM movie_embeddings
            WHERE movie_id = :movie_id
        )
        SELECT m.id,
               m.title,
               m.release_date,
               m.genres,
               m.keywords,
               m.runtime,
               m.original_language,
               m.vote_count,
               m.vote_average,
               (e.embedding <=> q.embedding) AS distance
        FROM movie_embeddings e
        JOIN movies m ON m.id = e.movie_id
        JOIN q ON TRUE
        WHERE e.movie_id != :movie_id
        ORDER BY e.embedding <=> q.embedding
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(q, {"movie_id": movie_id, "limit": k}).mappings().all()
    return [Candidate(**row) for row in rows]


def apply_rerank(anchor: MovieMetadata, candidates: list[Candidate], top_n: int) -> list[Candidate]:
    return rerank_candidates(anchor, candidates, top_n)
