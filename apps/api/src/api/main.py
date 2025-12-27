from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.config import SIM_CANDIDATES_K, SIM_RERANK_ENABLED, SIM_TOP_N
from api.config import FRONTEND_ORIGINS, TMDB_BACKDROP_SIZE, TMDB_IMAGE_BASE_URL, TMDB_POSTER_SIZE
from api.similarity import (
    EmbeddingNotFoundError,
    apply_rerank,
    fetch_movie_metadata,
    find_movie_id_by_title,
    get_similar_candidates,
)
from api.movies import fetch_movie_detail
from api.users import (
    MovieNotFoundError,
    UserNotFoundError,
    create_user,
    get_user_ratings,
    get_rating_queue,
    get_recommendations,
    get_profile_stats,
    get_next_movie,
    get_feed,
    get_user_movie_match,
    get_user_summary,
    recompute_profile,
    upsert_rating,
)

app = FastAPI(title="TMDB RecSys API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_image_urls(poster_path: str | None, backdrop_path: str | None) -> tuple[str | None, str | None]:
    poster_url = f"{TMDB_IMAGE_BASE_URL}{TMDB_POSTER_SIZE}{poster_path}" if poster_path else None
    backdrop_url = f"{TMDB_IMAGE_BASE_URL}{TMDB_BACKDROP_SIZE}{backdrop_path}" if backdrop_path else None
    return poster_url, backdrop_url


class SimilarMovie(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    distance: float
    score: float | None
    poster_url: str | None = None
    backdrop_url: str | None = None


class MovieLookup(BaseModel):
    id: int
    title: str | None


class MovieDetailResponse(BaseModel):
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
    poster_url: str | None
    backdrop_url: str | None


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


class RateMovieRequest(BaseModel):
    movie_id: int
    rating: int | None = Field(default=None, ge=0, le=5)
    status: str | None = None


class RecommendationResponse(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    distance: float
    similarity: float | None
    poster_url: str | None = None
    backdrop_url: str | None = None


class RatingQueueResponse(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    poster_url: str | None = None
    backdrop_url: str | None = None


class RatedMovieResponse(BaseModel):
    id: int
    title: str | None
    poster_url: str | None = None
    backdrop_url: str | None = None
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
    poster_url: str | None = None
    backdrop_url: str | None = None


class FeedItemResponse(BaseModel):
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    distance: float | None
    similarity: float | None
    source: str
    poster_url: str | None = None
    backdrop_url: str | None = None


class UserMovieMatchResponse(BaseModel):
    score: int | None


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

    responses = []
    for candidate in ranked:
        poster_url, backdrop_url = _build_image_urls(candidate.poster_path, candidate.backdrop_path)
        responses.append(
            SimilarMovie(
                id=candidate.id,
                title=candidate.title,
                release_date=candidate.release_date,
                genres=candidate.genres,
                distance=candidate.distance,
                score=candidate.score,
                poster_url=poster_url,
                backdrop_url=backdrop_url,
            )
        )
    return responses


@app.get("/movies/lookup", response_model=MovieLookup)
def lookup_movie(title: str = Query(min_length=1)):
    movie = find_movie_id_by_title(title)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return MovieLookup(id=movie.id, title=movie.title)


@app.get("/movies/{movie_id}", response_model=MovieDetailResponse)
def movie_detail(movie_id: int):
    movie = fetch_movie_detail(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    poster_url, backdrop_url = _build_image_urls(movie.poster_path, movie.backdrop_path)
    payload = movie.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url}
    return MovieDetailResponse(**payload)


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


@app.post("/users/{user_id}/rate")
def rate_movie_simple(user_id: int, payload: RateMovieRequest):
    if payload.rating is None and payload.status is None:
        raise HTTPException(status_code=400, detail="rating or status is required")

    status = payload.status or ("watched" if payload.rating is not None else "unwatched")
    if status not in {"watched", "unwatched"}:
        raise HTTPException(status_code=400, detail="status must be watched or unwatched")

    rating = payload.rating if status == "watched" else None
    try:
        upsert_rating(user_id, payload.movie_id, rating, status)
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
    responses = []
    for rec in recs:
        poster_url, backdrop_url = _build_image_urls(rec.poster_path, rec.backdrop_path)
        responses.append(
            RecommendationResponse(
                **(rec.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url})
            )
        )
    return responses


@app.get("/users/{user_id}/rating-queue", response_model=list[RatingQueueResponse])
def rating_queue(user_id: int, k: int = Query(default=20, ge=1, le=100)):
    try:
        queue = get_rating_queue(user_id, k)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    responses = []
    for item in queue:
        poster_url, backdrop_url = _build_image_urls(item.poster_path, item.backdrop_path)
        responses.append(
            RatingQueueResponse(
                **(item.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url})
            )
        )
    return responses


@app.get("/users/{user_id}/ratings", response_model=list[RatedMovieResponse])
def user_ratings(user_id: int, k: int = Query(default=20, ge=1, le=100)):
    try:
        ratings = get_user_ratings(user_id, k)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    responses = []
    for item in ratings:
        poster_url, backdrop_url = _build_image_urls(item.poster_path, item.backdrop_path)
        responses.append(
            RatedMovieResponse(
                **(item.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url})
            )
        )
    return responses


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
    poster_url, backdrop_url = _build_image_urls(movie.poster_path, movie.backdrop_path)
    return NextMovieResponse(**(movie.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url}))


@app.get("/users/{user_id}/feed", response_model=list[FeedItemResponse])
def user_feed(user_id: int, k: int = Query(default=20, ge=1, le=100)):
    try:
        items = get_feed(user_id, k)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    responses = []
    for item in items:
        poster_url, backdrop_url = _build_image_urls(item.poster_path, item.backdrop_path)
        responses.append(
            FeedItemResponse(
                **(item.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url})
            )
        )
    return responses


@app.get("/users/{user_id}/movies/{movie_id}/match", response_model=UserMovieMatchResponse)
def user_movie_match(user_id: int, movie_id: int):
    try:
        match = get_user_movie_match(user_id, movie_id)
    except (UserNotFoundError, MovieNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UserMovieMatchResponse(**match.__dict__)
