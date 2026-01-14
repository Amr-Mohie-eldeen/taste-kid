from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class UserNotFoundError(LookupError):
    pass


class MovieNotFoundError(LookupError):
    pass


@dataclass
class UserSummary:
    id: int
    display_name: str | None
    num_ratings: int
    profile_updated_at: str | None


@dataclass
class Recommendation:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    keywords: str | None
    runtime: int | None
    original_language: str | None
    vote_count: int | None
    poster_path: str | None
    backdrop_path: str | None
    distance: float
    dislike_distance: float | None = None
    similarity: float | None = None
    score: float | None = None


@dataclass
class RatingQueueItem:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    poster_path: str | None
    backdrop_path: str | None


@dataclass
class ProfileStats:
    user_id: int
    num_ratings: int
    num_liked: int
    embedding_norm: float | None
    updated_at: str | None


@dataclass
class NextMovie:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    poster_path: str | None
    backdrop_path: str | None
    source: str


@dataclass
class FeedItem:
    id: int
    title: str | None
    release_date: date | None
    genres: str | None
    poster_path: str | None
    backdrop_path: str | None
    distance: float | None
    similarity: float | None
    score: float | None
    source: str


@dataclass
class UserMovieMatch:
    score: float | None


@dataclass
class RatedMovie:
    id: int
    title: str | None
    poster_path: str | None
    backdrop_path: str | None
    rating: int | None
    status: str
    updated_at: str | None
