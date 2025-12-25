from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from api.config import SIM_CANDIDATES_K, SIM_RERANK_ENABLED, SIM_TOP_N
from api.similarity import (
    EmbeddingNotFoundError,
    apply_rerank,
    fetch_movie_metadata,
    find_movie_id_by_title,
    get_similar_candidates,
)

app = FastAPI(title="TMDB RecSys API")


class SimilarMovie(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    distance: float
    score: float | None


class MovieLookup(BaseModel):
    id: int
    title: str | None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/movies/{movie_id}/similar", response_model=list[SimilarMovie])
def similar_movies(movie_id: int, k: int | None = Query(default=None, ge=1, le=100)):
    top_n = k or SIM_TOP_N
    candidates_k = max(top_n, SIM_CANDIDATES_K)
    anchor = fetch_movie_metadata(movie_id)
    if not anchor:
        raise HTTPException(status_code=404, detail="Movie not found")

    try:
        candidates = get_similar_candidates(movie_id, k=candidates_k)
    except EmbeddingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if SIM_RERANK_ENABLED:
        ranked = apply_rerank(anchor, candidates, top_n)
    else:
        ranked = candidates[:top_n]
        for candidate in ranked:
            candidate.score = None

    return [
        SimilarMovie(
            id=candidate.id,
            title=candidate.title,
            release_date=candidate.release_date,
            genres=candidate.genres,
            distance=candidate.distance,
            score=candidate.score,
        )
        for candidate in ranked
    ]


@app.get("/movies/lookup", response_model=MovieLookup)
def lookup_movie(title: str = Query(min_length=1)):
    movie = find_movie_id_by_title(title)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return MovieLookup(id=movie.id, title=movie.title)
