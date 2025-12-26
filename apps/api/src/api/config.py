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
