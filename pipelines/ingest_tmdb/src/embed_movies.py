from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from build_doc import build_movie_doc
from embeddings.factory import make_provider


@dataclass(frozen=True)
class Settings:
    database_url: str
    batch_rows: int = 100
    max_doc_chars: int = 20000
    sleep_s: float = 0.0


def _repo_root():
    from pathlib import Path
    return Path(__file__).resolve().parents[3]


def _load_settings() -> Settings:
    root = _repo_root()
    load_dotenv(root / ".env")

    database_url = os.getenv(
        "DATABASE_URL",
        os.getenv("DATABASE_URL_LOCAL", "postgresql+psycopg://app:app@localhost:5432/tmdb"),
    )

    return Settings(
        database_url=database_url,
        batch_rows=int(os.getenv("EMBED_BATCH_ROWS", "100")),
        max_doc_chars=int(os.getenv("EMBED_MAX_DOC_CHARS", "20000")),
        sleep_s=float(os.getenv("EMBED_SLEEP_S", "0")),
    )


def _make_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _):
        register_vector(dbapi_conn)

    return engine


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _get_embedding_dim_from_db(conn) -> int:
    # pgvector stores the dimension in the type modifier (atttypmod - 4)
    q = text("""
        SELECT (a.atttypmod - 4) AS dims,
               pg_catalog.format_type(a.atttypid, a.atttypmod) AS type_repr
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'movie_embeddings'
          AND a.attname = 'embedding'
          AND n.nspname = 'public';
    """)
    row = conn.execute(q).mappings().one()
    type_repr = row.get("type_repr")
    if type_repr:
        import re

        match = re.search(r"vector\((\d+)\)", type_repr)
        if match:
            return int(match.group(1))
    return int(row["dims"])


def _fetch_movies_to_embed(conn, limit_n: int, offset_n: int) -> list[dict[str, Any]]:
    # We only embed movies that do not have an embedding yet OR whose doc_hash differs.
    # We compute doc_hash in Python, so here we just fetch movies and existing hash.
    q = text("""
        SELECT m.*, e.doc_hash AS existing_doc_hash
        FROM movies m
        LEFT JOIN movie_embeddings e ON e.movie_id = m.id
        WHERE m.release_date IS NOT NULL
          AND m.release_date <= CURRENT_DATE
        ORDER BY m.vote_average DESC NULLS LAST, m.vote_count DESC NULLS LAST
        LIMIT :n
        OFFSET :offset
    """)
    rows = conn.execute(q, {"n": limit_n, "offset": offset_n}).mappings().all()
    return [dict(r) for r in rows]


def _upsert_embedding(conn, movie_id: int, embedding: list[float], model_name: str, doc_hash: str) -> None:
    q = text("""
        INSERT INTO movie_embeddings (movie_id, embedding, embedding_model, doc_hash)
        VALUES (:movie_id, :embedding, :embedding_model, :doc_hash)
        ON CONFLICT (movie_id) DO UPDATE
          SET embedding = EXCLUDED.embedding,
              embedding_model = EXCLUDED.embedding_model,
              doc_hash = EXCLUDED.doc_hash,
              created_at = now()
    """)
    conn.execute(
        q,
        {
            "movie_id": movie_id,
            "embedding": embedding,
            "embedding_model": model_name,
            "doc_hash": doc_hash,
        },
    )


def main() -> None:
    s = _load_settings()
    engine = _make_engine(s.database_url)

    provider = make_provider()

    with engine.begin() as conn:
        db_dim = _get_embedding_dim_from_db(conn)

    prov_dim = provider.dimension()
    if prov_dim != db_dim:
        raise RuntimeError(
            f"Embedding dimension mismatch: provider={prov_dim} but DB column is vector({db_dim}). "
            f"Fix by changing model or recreating movie_embeddings.embedding dimension "
            f"(see src/reset_embeddings.py)."
        )

    done = 0
    skipped = 0
    started = time.time()

    offset = 0
    while True:
        with engine.begin() as conn:
            movies = _fetch_movies_to_embed(conn, s.batch_rows, offset)
            if not movies:
                break

            for m in movies:
                doc = build_movie_doc(m)
                if not doc:
                    skipped += 1
                    continue

                doc = doc[: s.max_doc_chars]
                doc_hash = _sha256(doc)

                existing_hash = m.get("existing_doc_hash")
                if existing_hash == doc_hash:
                    skipped += 1
                    continue

                emb = provider.embed_text(doc)
                _upsert_embedding(conn, int(m["id"]), emb, type(provider).__name__, doc_hash)
                done += 1

            print(f"Embedded: {done} | Skipped unchanged: {skipped}")

        offset += len(movies)

        if s.sleep_s:
            time.sleep(s.sleep_s)

    elapsed = time.time() - started
    print(f"Done. Embedded {done}. Skipped {skipped}. Elapsed {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
