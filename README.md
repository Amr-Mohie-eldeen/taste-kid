# Taste-Kid

Taste-Kid is a taste.io-style movie discovery app. It combines a FastAPI backend for recommendations with a React + Tailwind + shadcn frontend designed for a sleek, professional experience.

## Stack

- **Backend:** FastAPI, PostgreSQL + pgvector
- **Frontend:** React, Vite, Tailwind CSS, shadcn/ui
- **Auth:** Keycloak (OIDC)
- **Infra:** Docker Compose

## Quickstart (Docker)

```bash
make setup
make build
```

Then open:

- **Web:** http://localhost:5173
- **API:** http://localhost:8000/docs
- **Keycloak:** http://localhost:8080 (Admin: `admin`/`admin`)

## Makefile Commands

```bash
make help
```

Common targets:

- `make build`: build + start all services (including Keycloak)
- `make up`: start services (no build)
- `make down`: stop services
- `make logs`: tail logs
- `make git-sync`: sync `main` and prune deleted branches

## Environment

Copy `.env.example` to `.env` (or run `make setup`).

### Authentication (Keycloak)

The stack uses Keycloak for OIDC authentication.

URL topology (dev):

- Browser and web app use the public issuer: `http://localhost:8080/realms/taste-kid`
- API (inside docker) fetches JWKS from the internal hostname: `http://keycloak:8080/realms/taste-kid/protocol/openid-connect/certs`

Key vars:

- `KEYCLOAK_PORT`, `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`
- `KEYCLOAK_ISSUER_URL`, `KEYCLOAK_JWKS_URL`, `KEYCLOAK_AUDIENCE`
- `VITE_KEYCLOAK_ISSUER_URL`, `VITE_KEYCLOAK_CLIENT_ID`

### Core Variables

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`
- `API_PORT`
- `VITE_API_URL`: frontend API base; defaults to `http://localhost:8000` (the client appends `/v1`)

Note: the web container bakes `VITE_*` values at build time.

### Recommendation tuning (optional)

- `DISLIKE_WEIGHT`, `DISLIKE_MIN_COUNT`, `NEUTRAL_RATING_WEIGHT`
- `SCORING_CONTEXT_LIMIT`, `RERANK_FETCH_MULTIPLIER`, `MAX_FETCH_CANDIDATES`
- `MAX_SCORING_GENRES`, `MAX_SCORING_KEYWORDS`

## Frontend

The frontend lives in `apps/web` and is fully containerized.

Auth behavior:

- Login and registration are handled by Keycloak (OIDC).
- The UI redirects to Keycloak; local email/password auth is not used.

Local dev:

```bash
cd apps/web
npm install
npm run dev
```

Theme tokens live in `apps/web/src/index.css`. Toggle the graphite theme by adding
`class="theme-graphite"` to `apps/web/index.html`.

## Backend

The FastAPI app lives in `apps/api`. API docs are available at `http://localhost:8000/docs`.

Auth behavior:

- The API verifies RS256 access tokens via JWKS.
- `/v1/auth/login` and `/v1/auth/register` return `410 Gone` when Keycloak is enabled.

## Services

`docker-compose.yml` includes:

- `postgres` (pgvector)
- `keycloak` (OIDC provider)
- `api` (FastAPI)
- `web` (nginx serving Vite build)
- `ollama` (optional embeddings provider)

## Database Bootstrap

- `infra/db/init.sql` is used for a fresh Postgres volume.
- The API also runs idempotent startup DDL to ensure required tables like `user_identities` exist.
  This does not wipe existing data.

## Pipelines

Data pipelines live in `pipelines/ingest_tmdb` and cover both ingestion and embeddings.

1) Ingest TMDB data (CSV -> Postgres):

```bash
cd pipelines/ingest_tmdb
uv run python src/ingest.py
```

2) Generate embeddings (movies -> `movie_embeddings`):

```bash
cd pipelines/ingest_tmdb
uv run python src/embed_movies.py
```

3) Reset embeddings table (when switching embedding models/dimensions):

```bash
cd pipelines/ingest_tmdb
uv run python src/reset_embeddings.py
```

Embedding providers are configured via env vars in `.env`:

- `EMBEDDINGS_PROVIDER` (`ollama` or `bedrock`)
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `AWS_REGION`, `BEDROCK_EMBED_MODEL_ID`
- `EMBEDDING_DIM`

## License

Private repository. All rights reserved.
