from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from api.config import DATABASE_URL


_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _ENGINE
