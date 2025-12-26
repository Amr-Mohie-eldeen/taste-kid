from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text

from api.db import get_engine


@dataclass
class MovieDetail:
    id: int
    title: str | None
    original_title: str | None
    release_date: date | None
    genres: str | None
    overview: str | None
    tagline: str | None
    runtime: int | None
    original_language: str | None
    vote_average: float | None
    vote_count: int | None
    poster_path: str | None
    backdrop_path: str | None


def fetch_movie_detail(movie_id: int) -> MovieDetail | None:
    engine = get_engine()
    q = text(
        """
        SELECT id,
               title,
               original_title,
               release_date,
               genres,
               overview,
               tagline,
               runtime,
               original_language,
               vote_average,
               vote_count,
               poster_path,
               backdrop_path
        FROM movies
        WHERE id = :movie_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(q, {"movie_id": movie_id}).mappings().first()
    if not row:
        return None
    return MovieDetail(**row)
