# Taste‑Kid

Taste‑Kid is a taste.io‑style movie discovery app. It combines a FastAPI backend for recommendations with a React + Tailwind + shadcn frontend designed for a sleek, professional experience.

## Stack

- **Backend:** FastAPI, PostgreSQL + pgvector
- **Frontend:** React, Vite, Tailwind CSS, shadcn/ui
- **Infra:** Docker Compose

## Quickstart (Docker)

```bash
make setup
make build
```

Then open:

- **Web:** http://localhost:5173
- **API:** http://localhost:8000/docs

## Makefile Commands

```bash
make help
```

Common targets:

- `make build`: build + start all services
- `make up`: start services (no build)
- `make down`: stop services
- `make logs`: tail logs

## Environment

Copy `.env.example` to `.env` (or run `make setup`).

Key variables used by the stack:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`
- `API_PORT`
- `VITE_API_URL` (frontend API base; defaults to `http://localhost:8000`)

## Frontend

The frontend lives in `apps/web` and is fully containerized. If you want local dev:

```bash
cd apps/web
npm install
npm run dev
```

Theme tokens live in `apps/web/src/index.css`. Toggle the graphite theme by adding
`class="theme-graphite"` to `apps/web/index.html`.

## Backend

The FastAPI app lives in `apps/api`. API docs are available at `http://localhost:8000/docs`.

## Services

`docker-compose.yml` includes:

- `postgres` (pgvector)
- `api` (FastAPI)
- `web` (nginx serving Vite build)
- `ollama` (optional embeddings provider)

## Pipelines

Data pipelines live in `pipelines/ingest_tmdb` and cover both ingestion and embeddings.

**1) Ingest TMDB data** (CSV → Postgres):

```bash
cd pipelines/ingest_tmdb
uv run python src/ingest.py
```

**2) Generate embeddings** (movies → `movie_embeddings`):

```bash
cd pipelines/ingest_tmdb
uv run python src/embed_movies.py
```

**3) Reset embeddings table** (when switching embedding models/dimensions):

```bash
cd pipelines/ingest_tmdb
uv run python src/reset_embeddings.py
```

Embedding providers are configured via environment variables in `.env`:

- `EMBEDDINGS_PROVIDER` (`ollama` or `bedrock`)
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `AWS_REGION`, `BEDROCK_EMBED_MODEL_ID`
- `EMBEDDING_DIM`

## Deployment Notes

- The web container uses `VITE_API_URL` at build time.
- The API uses `FRONTEND_ORIGINS` to allow local frontend origins.

## License

Private repository. All rights reserved.
