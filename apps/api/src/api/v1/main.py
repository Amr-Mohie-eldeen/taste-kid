from datetime import date
from typing import Any, Generic, TypeVar

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.config import (
    SIM_CANDIDATES_K,
    SIM_RERANK_ENABLED,
    SIM_TOP_N,
    TMDB_BACKDROP_SIZE,
    TMDB_IMAGE_BASE_URL,
    TMDB_POSTER_SIZE,
)
from api.movies import fetch_movie_detail
from api.similarity import (
    apply_rerank,
    fetch_movie_metadata,
    find_movie_id_by_title,
    get_similar_candidates,
)
from api.users import (
    create_user,
    get_feed,
    get_next_movie,
    get_profile_stats,
    get_rating_queue,
    get_recommendations,
    get_user_movie_match,
    get_user_ratings,
    get_user_summary,
    recompute_profile,
    upsert_rating,
)

router = APIRouter()

ResponseData = TypeVar("ResponseData")


class ResponseEnvelope(BaseModel, Generic[ResponseData]):
    data: ResponseData
    meta: dict[str, Any] = Field(default_factory=dict)


def _build_image_urls(poster_path: str | None, backdrop_path: str | None) -> tuple[str | None, str | None]:
    poster_url = f"{TMDB_IMAGE_BASE_URL}{TMDB_POSTER_SIZE}{poster_path}" if poster_path else None
    backdrop_url = f"{TMDB_IMAGE_BASE_URL}{TMDB_BACKDROP_SIZE}{backdrop_path}" if backdrop_path else None
    return poster_url, backdrop_url


def _with_image_urls(item) -> dict:
    poster_url, backdrop_url = _build_image_urls(item.poster_path, item.backdrop_path)
    return item.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url}


def _map_with_image_urls(items, response_cls):
    return [response_cls(**_with_image_urls(item)) for item in items]


def _envelope(data: ResponseData, meta: dict[str, Any] | None = None) -> ResponseEnvelope[ResponseData]:
    return ResponseEnvelope(data=data, meta=meta or {})


def _paginate(items: list[ResponseData], cursor: int, limit: int) -> tuple[list[ResponseData], dict[str, Any]]:
    has_more = len(items) > limit
    page_items = items[:limit]
    next_cursor = str(cursor + limit) if has_more else None
    return page_items, {"next_cursor": next_cursor, "has_more": has_more}


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
    score: float | None = None
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
    score: float | None = None
    source: str
    poster_url: str | None = None
    backdrop_url: str | None = None


class UserMovieMatchResponse(BaseModel):
    score: float | None


def _process_rating(user_id: int, movie_id: int, rating: int | None, status: str | None):
    if rating is None and status is None:
        raise HTTPException(status_code=400, detail="rating or status is required")

    resolved_status = status or ("watched" if rating is not None else "unwatched")
    if resolved_status not in {"watched", "unwatched"}:
        raise HTTPException(status_code=400, detail="status must be watched or unwatched")

    resolved_rating = rating if resolved_status == "watched" else None
    upsert_rating(user_id, movie_id, resolved_rating, resolved_status)
    recompute_profile(user_id)
    return _envelope({"status": "ok"})


@router.get("/health", response_model=ResponseEnvelope[dict[str, str]])
def health():
    return _envelope({"status": "ok"})


@router.get("/movies/{movie_id}/similar", response_model=ResponseEnvelope[list[SimilarMovie]])
def similar_movies(
    movie_id: int,
    k: int | None = Query(default=None, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
):
    page_size = k or SIM_TOP_N
    requested = page_size + cursor + 1
    candidates_k = max(requested, SIM_CANDIDATES_K)
    anchor = fetch_movie_metadata(movie_id)
    if not anchor:
        raise HTTPException(status_code=404, detail="Movie not found")

    candidates = get_similar_candidates(movie_id, k=candidates_k)

    if SIM_RERANK_ENABLED:
        ranked = apply_rerank(anchor, candidates, requested)
    else:
        ranked = candidates[:requested]
        for candidate in ranked:
            candidate.score = None

    page_candidates, meta = _paginate(ranked[cursor:], cursor, page_size)
    return _envelope(_map_with_image_urls(page_candidates, SimilarMovie), meta)


@router.get("/movies/lookup", response_model=ResponseEnvelope[MovieLookup])
def lookup_movie(title: str = Query(min_length=1)):
    movie = find_movie_id_by_title(title)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _envelope(MovieLookup(id=movie.id, title=movie.title))


@router.get("/movies/{movie_id}", response_model=ResponseEnvelope[MovieDetailResponse])
def movie_detail(movie_id: int):
    movie = fetch_movie_detail(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    poster_url, backdrop_url = _build_image_urls(movie.poster_path, movie.backdrop_path)
    payload = movie.__dict__ | {"poster_url": poster_url, "backdrop_url": backdrop_url}
    return _envelope(MovieDetailResponse(**payload))


@router.post("/users", response_model=ResponseEnvelope[UserSummaryResponse])
def create_user_profile(payload: UserCreateRequest):
    user_id = create_user(payload.display_name)
    summary = get_user_summary(user_id)
    return _envelope(UserSummaryResponse(**summary.__dict__))


@router.get("/users/{user_id}", response_model=ResponseEnvelope[UserSummaryResponse])
def get_user_profile(user_id: int):
    summary = get_user_summary(user_id)
    return _envelope(UserSummaryResponse(**summary.__dict__))


@router.put("/users/{user_id}/ratings/{movie_id}", response_model=ResponseEnvelope[dict[str, str]])
def rate_movie(user_id: int, movie_id: int, payload: RatingRequest):
    return _process_rating(user_id, movie_id, payload.rating, payload.status)


@router.post("/users/{user_id}/rate", response_model=ResponseEnvelope[dict[str, str]])
def rate_movie_simple(user_id: int, payload: RateMovieRequest):
    return _process_rating(user_id, payload.movie_id, payload.rating, payload.status)


@router.get("/users/{user_id}/recommendations", response_model=ResponseEnvelope[list[RecommendationResponse]])
def user_recommendations(
    user_id: int,
    k: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
):
    recs = get_recommendations(user_id, k + 1, cursor)
    page_recs, meta = _paginate(recs, cursor, k)
    return _envelope(_map_with_image_urls(page_recs, RecommendationResponse), meta)


@router.get("/users/{user_id}/rating-queue", response_model=ResponseEnvelope[list[RatingQueueResponse]])
def rating_queue(
    user_id: int,
    k: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
):
    queue = get_rating_queue(user_id, k + 1, cursor)
    page_queue, meta = _paginate(queue, cursor, k)
    return _envelope(_map_with_image_urls(page_queue, RatingQueueResponse), meta)


@router.get("/users/{user_id}/ratings", response_model=ResponseEnvelope[list[RatedMovieResponse]])
def user_ratings(
    user_id: int,
    k: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
):
    ratings = get_user_ratings(user_id, k + 1, cursor)
    page_ratings, meta = _paginate(ratings, cursor, k)
    return _envelope(_map_with_image_urls(page_ratings, RatedMovieResponse), meta)


@router.get("/users/{user_id}/profile", response_model=ResponseEnvelope[ProfileStatsResponse])
def profile_stats(user_id: int):
    stats = get_profile_stats(user_id)
    return _envelope(ProfileStatsResponse(**stats.__dict__))


@router.get("/users/{user_id}/next", response_model=ResponseEnvelope[NextMovieResponse])
def next_movie(user_id: int):
    movie = get_next_movie(user_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="No more unrated movies")
    return _envelope(NextMovieResponse(**_with_image_urls(movie)))


@router.get("/users/{user_id}/feed", response_model=ResponseEnvelope[list[FeedItemResponse]])
def user_feed(
    user_id: int,
    k: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
):
    items = get_feed(user_id, k + 1, cursor)
    page_items, meta = _paginate(items, cursor, k)
    return _envelope(_map_with_image_urls(page_items, FeedItemResponse), meta)


@router.get("/users/{user_id}/movies/{movie_id}/match", response_model=ResponseEnvelope[UserMovieMatchResponse])
def user_movie_match(user_id: int, movie_id: int):
    match = get_user_movie_match(user_id, movie_id)
    return _envelope(UserMovieMatchResponse(**match.__dict__))
