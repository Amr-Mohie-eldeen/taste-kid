from __future__ import annotations

from api.users.db import create_user, get_user_summary
from api.users.match import get_user_movie_match
from api.users.profile import get_profile_stats, recompute_profile
from api.users.queue import get_feed, get_next_movie, get_rating_queue
from api.users.ratings import get_user_ratings, upsert_rating
from api.users.recommendations import get_recommendations, get_recommendations_page
from api.users.types import (
    FeedItem,
    MovieNotFoundError,
    NextMovie,
    ProfileStats,
    RatedMovie,
    RatingQueueItem,
    Recommendation,
    UserMovieMatch,
    UserNotFoundError,
    UserSummary,
)

__all__ = [
    "MovieNotFoundError",
    "UserNotFoundError",
    "FeedItem",
    "NextMovie",
    "ProfileStats",
    "RatedMovie",
    "RatingQueueItem",
    "Recommendation",
    "UserMovieMatch",
    "UserSummary",
    "create_user",
    "get_feed",
    "get_next_movie",
    "get_profile_stats",
    "get_rating_queue",
    "get_recommendations",
    "get_recommendations_page",
    "get_user_movie_match",
    "get_user_ratings",
    "get_user_summary",
    "recompute_profile",
    "upsert_rating",
]
