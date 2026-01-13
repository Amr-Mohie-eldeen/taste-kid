# AGENTS.md

This repo contains:
- `apps/api`: FastAPI + Postgres/pgvector backend (Python, `uv`, Ruff, Pyright, Pytest)
- `apps/web`: React/Vite + Tailwind frontend (TypeScript)
- `pipelines/ingest_tmdb`: ingestion/embedding jobs (Python, `uv`)

This file is guidance for agentic coding tools operating in this repo.

## Quick Commands (Start Here)

### Full stack (Docker Compose, repo root)
- `make setup` (creates `.env` from `.env.example` if missing)
- `make build` (build + start everything)
- `make up` / `make down` / `make restart`
- `make logs` / `make logs-api` / `make logs-web` / `make logs-db`

### API checks (repo root)
- `make lint-api` (Ruff lint)
- `make format-api` (Ruff format)
- `make check-api-types` (Pyright)
- `make test-api` (Pytest)
- `make ci-api` (lint + types + tests)

### Web (apps/web)
- `npm install`
- `npm run dev` (Vite dev server)
- `npm run build` (runs `tsc -b` then `vite build`)
- `npm run preview`

### Pipelines (pipelines/ingest_tmdb)
- `uv run python src/ingest.py`
- `uv run python src/embed_movies.py`
- `uv run python src/reset_embeddings.py`

## Running a Single Test (API)

API tests live in `apps/api/tests` and are executed via `uv run pytest`.

From repo root:
- `make test-api` (all tests)

From `apps/api`:
- Run a single test file: `uv run pytest tests/test_users.py`
- Run a single test function: `uv run pytest tests/test_users.py::test_create_user`
- Run by substring match: `uv run pytest -k "create_user"`
- Useful flags: `-vv`, `-x`, `--maxfail=1`, `-s`

Notes:
- Tests use `testcontainers` and require Docker to be installed and running.
- The integration DB is a `pgvector/pgvector:pg16` container started by the suite.

## Lint / Format / Types

### Backend (apps/api)
Defined in `apps/api/Makefile`:
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Types: `uv run pyright`

Tool config is in `apps/api/pyproject.toml`:
- Ruff: `line-length = 100`, `target-version = py311`, lint selects include `E/W/F/I/B/C4/UP/ARG/PTH`, ignores `E501` and `B008`.
- Pyright: `typeCheckingMode = standard`, `pythonVersion = 3.11`, `include = ["src"]`.
- Pytest: `asyncio_mode = auto`, `testpaths = ["tests"]`, `pythonpath = ["src"]`.

### Frontend (apps/web)
- No ESLint/Prettier configured.
- Type-checking happens via `npm run build` (runs `tsc -b`).

### Pipelines (pipelines/ingest_tmdb)
- No lint/type/test automation configured.
- Prefer running scripts via `uv run` so dependencies match `pyproject.toml`.

## Smoke / Demo Scripts

These assume the API is running and require `jq`:
- `scripts/test_retrieval.sh "Movie Title"` (uses `BASE_URL`, default `http://localhost:8000`)
- `scripts/smoke_user_flow.sh`
- `scripts/user_recs_demo.sh`

## Repo Layout
- `apps/web/src`: React pages/components, API client in `apps/web/src/lib/api.ts`
- `apps/api/src/api`: FastAPI app, routes under `/v1`
- `infra/db/init.sql`: schema/bootstrap SQL used by Postgres and tests

## Code Style Guidelines

### General
- Prefer small, focused changes; avoid drive-by refactors.
- Mirror API payload shapes consistently across frontend/backend.
- Avoid adding new tooling (linters/formatters) unless requested.

### Python (apps/api)
**Imports**
- Order: stdlib, blank line, third-party, blank line, local `api.*`.
- Use absolute imports from the `api` package (`from api.config import ...`).

**Formatting**
- 4-space indentation.
- Follow Ruff formatting; do not hand-format against it.
- Keep SQL in triple-quoted strings aligned with SQL keywords.

**Types**
- Prefer `str | None` over `Optional[str]` (Python 3.11 style).
- Use `dataclass` for internal row/result models.
- Use Pydantic `BaseModel` for request/response schemas.

**Error handling**
- Raise `fastapi.HTTPException` for 4xx.
- Prefer domain exceptions (`UserNotFoundError`, `MovieNotFoundError`, etc.) and map them centrally (see `api.main`).
- Keep error codes stable (`USER_NOT_FOUND`, `MOVIE_NOT_FOUND`, etc.).
- Responses use an envelope: `{"data": ..., "meta": ...}`.

**Database**
- Use parameterized queries (`sqlalchemy.text`) inside `engine.begin()`.
- Avoid string interpolation in SQL.

**Logging**
- Use `logger = logging.getLogger("api")`.
- Request logging attaches `X-Request-ID` via request context.

### TypeScript/React (apps/web)
**Imports**
- Third-party imports first, then local modules.
- Use `import type` for type-only imports.

**Formatting**
- 2-space indentation.
- Double quotes; semicolons.
- Wrap long JSX props; keep class strings readable.

**Types & naming**
- Prefer `type` aliases; avoid `any`.
- Use explicit unions and nullable types (`string | null`).
- camelCase for functions/vars; PascalCase for components/types.
- Keep API field names in `snake_case` to match backend payloads.

**App structure**
- Centralize routes in `apps/web/src/App.tsx`.
- Use React Query for async caching.
- Centralize API calls in `apps/web/src/lib/api.ts`.

**Styling**
- Tailwind classes drive layout/colors; theme tokens in `apps/web/src/index.css`.

## Cursor / Copilot Rules
- No `.cursorrules`, `.cursor/rules/*`, or `.github/copilot-instructions.md` found in this repo.
- If you add any, update this file to reflect them.
