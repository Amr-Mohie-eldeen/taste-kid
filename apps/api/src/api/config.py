import os


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_env(name: str, default: float, min_val: float | None = None, max_val: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: '{raw}' is not a valid float") from exc
    if min_val is not None and value < min_val:
        raise ValueError(f"Invalid {name}: {value} is below minimum {min_val}")
    if max_val is not None and value > max_val:
        raise ValueError(f"Invalid {name}: {value} exceeds maximum {max_val}")
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/tmdb")
SIM_CANDIDATES_K = int(os.getenv("SIM_CANDIDATES_K", "200"))
SIM_TOP_N = int(os.getenv("SIM_TOP_N", "20"))
SIM_RERANK_ENABLED = _bool_env("SIM_RERANK_ENABLED", True)
USER_UNWATCHED_COOLDOWN_DAYS = int(os.getenv("USER_UNWATCHED_COOLDOWN_DAYS", "90"))
TMDB_IMAGE_BASE_URL = os.getenv("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/")
TMDB_POSTER_SIZE = os.getenv("TMDB_POSTER_SIZE", "w500")
TMDB_BACKDROP_SIZE = os.getenv("TMDB_BACKDROP_SIZE", "w780")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_REQUEST_SAMPLE_RATE = _float_env("LOG_REQUEST_SAMPLE_RATE", 1.0, min_val=0.0, max_val=1.0)
LOG_SLOW_REQUEST_MS = _float_env("LOG_SLOW_REQUEST_MS", 500.0, min_val=0.0)
# Set to 0 or lower to log all queries.
LOG_DB_SLOW_QUERY_MS = _float_env("LOG_DB_SLOW_QUERY_MS", 250.0)
DISLIKE_WEIGHT = _float_env("DISLIKE_WEIGHT", 0.5, min_val=0.0)
DISLIKE_MIN_COUNT = int(os.getenv("DISLIKE_MIN_COUNT", "3"))
NEUTRAL_RATING_WEIGHT = _float_env("NEUTRAL_RATING_WEIGHT", 0.2, min_val=0.0, max_val=1.0)
