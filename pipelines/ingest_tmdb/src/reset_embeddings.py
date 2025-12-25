from __future__ import annotations

from sqlalchemy import text

from embed_movies import _load_settings, _make_engine
from embeddings.factory import make_provider


def main() -> None:
    settings = _load_settings()
    provider = make_provider()
    new_dim = int(provider.dimension())

    if new_dim <= 0:
        raise ValueError(f"Invalid embedding dimension: {new_dim}")

    engine = _make_engine(settings.database_url)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("DROP TABLE IF EXISTS movie_embeddings"))
        conn.execute(
            text(
                f"""
                CREATE TABLE movie_embeddings (
                    movie_id BIGINT PRIMARY KEY,
                    embedding vector({new_dim}),
                    embedding_model TEXT NOT NULL,
                    doc_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )

    print(f"movie_embeddings recreated with vector({new_dim}).")


if __name__ == "__main__":
    main()
