from __future__ import annotations

from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from api.config import DATABASE_URL


_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)

        @event.listens_for(_ENGINE, "connect")
        def _on_connect(dbapi_conn, _):
            register_vector(dbapi_conn)
    return _ENGINE
