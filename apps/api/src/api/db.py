from __future__ import annotations

import logging
import time

from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from api.config import DATABASE_URL, LOG_DB_SLOW_QUERY_MS


_ENGINE: Engine | None = None
_logger = logging.getLogger("db")


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)

        @event.listens_for(_ENGINE, "connect")
        def _on_connect(dbapi_conn, _):
            register_vector(dbapi_conn)

        @event.listens_for(_ENGINE, "before_cursor_execute")
        def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info["query_start_time"] = time.perf_counter()

        @event.listens_for(_ENGINE, "after_cursor_execute")
        def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            start = conn.info.pop("query_start_time", None)
            if start is None:
                return
            duration_ms = (time.perf_counter() - start) * 1000
            # LOG_DB_SLOW_QUERY_MS <= 0 logs all queries.
            if LOG_DB_SLOW_QUERY_MS <= 0 or duration_ms >= LOG_DB_SLOW_QUERY_MS:
                _logger.info(
                    "db_query",
                    extra={
                        "duration_ms": round(duration_ms, 2),
                        "statement": statement.strip()[:500],
                        "executemany": executemany,
                    },
                )
    return _ENGINE
