# pipelines/ingest_tmdb AGENTS

Standalone ingestion + embedding scripts. Writes to the same Postgres schema as the API.

## Commands (from `pipelines/ingest_tmdb`)
- `uv run python src/ingest.py`
- `uv run python src/embed_movies.py`
- `uv run python src/reset_embeddings.py`

## Where To Look
- CSV ingestion -> `movies`: `pipelines/ingest_tmdb/src/ingest.py`
- Embedding generation -> `movie_embeddings`: `pipelines/ingest_tmdb/src/embed_movies.py`
- Destructive reset of embeddings table: `pipelines/ingest_tmdb/src/reset_embeddings.py`
- Shared schema: `infra/db/init.sql`

## Conventions
- Run via `uv run` so dependencies match `pipelines/ingest_tmdb/pyproject.toml`.
- Embedding dimension is controlled by `EMBEDDING_DIM` (default 768).

## Anti-Patterns / Safety
- `src/reset_embeddings.py` is destructive; only use for embedding model/dimension migrations.
- Don’t import from `apps/api`; pipelines are standalone.
