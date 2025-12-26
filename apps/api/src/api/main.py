from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from api.config import SIM_CANDIDATES_K, SIM_RERANK_ENABLED, SIM_TOP_N
from api.similarity import (
    EmbeddingNotFoundError,
    apply_rerank,
    fetch_movie_metadata,
    find_movie_id_by_title,
    get_similar_candidates,
)
from api.users import (
    MovieNotFoundError,
    UserNotFoundError,
    create_user,
    get_user_ratings,
    get_rating_queue,
    get_recommendations,
    get_profile_stats,
    get_next_movie,
    get_user_summary,
    recompute_profile,
    upsert_rating,
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


class UserCreateRequest(BaseModel):
    display_name: str | None = None


class UserSummaryResponse(BaseModel):
    id: int
    display_name: str | None
    num_ratings: int
    profile_updated_at: str | None


class RatingRequest(BaseModel):
    rating: int | None = Field(default=None, ge=0, le=5)
    status: str | None = None


class RecommendationResponse(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    distance: float
    similarity: float | None


class RatingQueueResponse(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None


class RatedMovieResponse(BaseModel):
    id: int
    title: str | None
    rating: int | None
    status: str
    updated_at: str | None


class ProfileStatsResponse(BaseModel):
    user_id: int
    num_ratings: int
    num_liked: int
    embedding_norm: float | None
    updated_at: str | None


class NextMovieResponse(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    source: str


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


@app.post("/users", response_model=UserSummaryResponse)
def create_user_profile(payload: UserCreateRequest):
    user_id = create_user(payload.display_name)
    summary = get_user_summary(user_id)
    return UserSummaryResponse(**summary.__dict__)


@app.get("/users/{user_id}", response_model=UserSummaryResponse)
def get_user_profile(user_id: int):
    try:
        summary = get_user_summary(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UserSummaryResponse(**summary.__dict__)


@app.put("/users/{user_id}/ratings/{movie_id}")
def rate_movie(user_id: int, movie_id: int, payload: RatingRequest):
    if payload.rating is None and payload.status is None:
        raise HTTPException(status_code=400, detail="rating or status is required")

    status = payload.status or ("watched" if payload.rating is not None else "unwatched")
    if status not in {"watched", "unwatched"}:
        raise HTTPException(status_code=400, detail="status must be watched or unwatched")

    rating = payload.rating if status == "watched" else None
    try:
        upsert_rating(user_id, movie_id, rating, status)
    except (UserNotFoundError, MovieNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    recompute_profile(user_id)
    return {"status": "ok"}


@app.get("/users/{user_id}/recommendations", response_model=list[RecommendationResponse])
def user_recommendations(user_id: int, k: int = Query(default=20, ge=1, le=100)):
    try:
        recs = get_recommendations(user_id, k)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [RecommendationResponse(**rec.__dict__) for rec in recs]


@app.get("/users/{user_id}/rating-queue", response_model=list[RatingQueueResponse])
def rating_queue(user_id: int, k: int = Query(default=20, ge=1, le=100)):
    try:
        queue = get_rating_queue(user_id, k)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [RatingQueueResponse(**item.__dict__) for item in queue]


@app.get("/users/{user_id}/ratings", response_model=list[RatedMovieResponse])
def user_ratings(user_id: int, k: int = Query(default=20, ge=1, le=100)):
    try:
        ratings = get_user_ratings(user_id, k)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [RatedMovieResponse(**item.__dict__) for item in ratings]


@app.get("/users/{user_id}/profile", response_model=ProfileStatsResponse)
def profile_stats(user_id: int):
    try:
        stats = get_profile_stats(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProfileStatsResponse(**stats.__dict__)


@app.get("/users/{user_id}/next", response_model=NextMovieResponse)
def next_movie(user_id: int):
    try:
        movie = get_next_movie(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if movie is None:
        raise HTTPException(status_code=404, detail="No more unrated movies")
    return NextMovieResponse(**movie.__dict__)
