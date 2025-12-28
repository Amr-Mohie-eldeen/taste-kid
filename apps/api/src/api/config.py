import os


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


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
LOG_REQUEST_SAMPLE_RATE = float(os.getenv("LOG_REQUEST_SAMPLE_RATE", "1"))
LOG_SLOW_REQUEST_MS = float(os.getenv("LOG_SLOW_REQUEST_MS", "500"))
LOG_DB_SLOW_QUERY_MS = float(os.getenv("LOG_DB_SLOW_QUERY_MS", "250"))
