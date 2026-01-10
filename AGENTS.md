# AGENTS.md

This repository contains a FastAPI + Postgres backend, a React/Vite frontend, and data pipelines.
Use the notes below when making changes in this repo.

## Build, Run, Lint, Test

### Docker / Full Stack (repo root)
- `make setup` - copy `.env.example` to `.env` if missing.
- `make build` - build and start all services via Docker Compose.
- `make up` - start services without rebuild.
- `make down` - stop and remove containers.
- `make logs` - follow all services.
- `make logs-api` / `make logs-web` / `make logs-db` - follow a single service.

### Frontend (apps/web)
- Install deps: `npm install`
- Dev server: `npm run dev`
- Production build (also runs `tsc`): `npm run build`
- Preview build: `npm run preview`

**Linting:** no ESLint/Prettier configured. Use `npm run build` for type-checking.
**Tests:** no frontend test runner configured.
**Single test:** not applicable (no test framework); use targeted UI/manual checks instead.

### Backend (apps/api)
- The Docker image runs: `uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log`
- Local run (suggested): `uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
- Dependencies managed via `uv` + `pyproject.toml` (`uv sync` in Dockerfile).

**Linting:** none configured.
**Tests:** none configured.
**Single test:** not applicable (no test framework). Use smoke checks via the API or `scripts/test_retrieval.sh`.

### Data Pipelines (pipelines/ingest_tmdb)
- Ingest TMDB data: `uv run python src/ingest.py`
- Generate embeddings: `uv run python src/embed_movies.py`
- Reset embeddings table: `uv run python src/reset_embeddings.py`

### Scripts / Smoke Checks
- Similarity smoke test: `scripts/test_retrieval.sh "Movie Title"`
  - Uses `BASE_URL` env var (defaults to `http://localhost:8000`).
  - Requires `jq` installed.

## Repo Layout
- `apps/web` - React + Vite frontend.
- `apps/api` - FastAPI service (`src/api`).
- `pipelines/ingest_tmdb` - ingestion + embeddings jobs.
- `scripts` - ad-hoc helpers (shell scripts).
- `data` - local datasets/artifacts.
- `infra` - infra/devops helpers.
- `docs` - product/architecture notes.

## Git Workflow
- Use short-lived feature branches (no direct commits to `main`).
- Open GitHub issues for product/behavior changes before coding.
- Require pull requests for non-doc changes; docs-only updates can merge directly if needed.
- Keep PRs scoped and include context, screenshots, or API examples when relevant.
- Follow existing commit style: `<type>: <summary>` (e.g. `docs: update README`, `chore: add logging`).

## Code Style Guidelines

### General
- Prefer small, focused changes scoped to a single feature or bug.
- Keep behavior consistent with existing response shapes and UI styling.
- Update related types or schemas when you change API payloads.
- Avoid adding new tooling (linters/formatters) unless requested.

### Frontend (apps/web)
**Imports**
- Order imports: third-party packages first, then local modules.
- Use `import type` for type-only imports (see `src/types.ts`).
- Prefer named exports for components/utilities; default export only for `App`.

**Formatting**
- 2-space indentation.
- Double quotes for strings.
- Semicolons at statement ends.
- Wrap long JSX props across lines, align closing brackets.

**React + TypeScript**
- Components use PascalCase filenames and exported functions (e.g. `AppShell`).
- Hooks use `use*` naming (`useStore`).
- Types are `type` aliases unless an interface fits better (see `lib/api.ts`).
- Avoid `any`; use explicit unions and nullable types (`string | null`).
- Keep API responses typed and mirrored to backend schemas.

**Routing + Layout**
- Keep route definitions centralized in `src/App.tsx`.
- Layout components live in `src/components` and wrap pages via `Outlet`.

**State + Data Fetching**
- React Query is the primary async cache (`QueryClientProvider`, `useQuery`).
- Centralize API access in `src/lib/api.ts`.
- Use `ApiError` for API failures and handle missing data explicitly.
- The client appends `/v1` to `VITE_API_URL` if missing.
- Keep pagination wired to `cursor` + `k` query params.

**Styling**
- Tailwind classes drive layout and colors; keep class strings readable.
- Theme tokens live in `src/index.css` and are applied via CSS variables.
- Avoid inline styles unless necessary; prefer utility classes.

**Naming**
- camelCase for variables/functions.
- PascalCase for React components and types.
- Keep API field names in snake_case to match backend payloads.

### Backend (apps/api)
**Imports**
- Standard library imports first, blank line, third-party imports, blank line, local `api.*` imports.
- Use absolute imports from `api` package (e.g. `from api.config import ...`).

**Formatting**
- 4-space indentation.
- Use type hints for public functions and dataclasses.
- Keep SQL strings in triple-quoted blocks aligned with the SQL keywords.

**Types + Models**
- Use `dataclass` for internal row models (`users.py`, `similarity.py`).
- Use Pydantic `BaseModel` for request/response schemas in API routes.
- Prefer `str | None` unions instead of `Optional[str]` (Python 3.11 style).

**Error Handling + Responses**
- API responses use an envelope `{"data": ..., "meta": ...}`.
- Raise `HTTPException` for 4xx errors; rely on global handlers for formatting.
- Custom domain errors (`UserNotFoundError`, `MovieNotFoundError`) are mapped to 404s in `api.main`.
- Always return consistent error codes (`USER_NOT_FOUND`, `MOVIE_NOT_FOUND`, etc.).
- Pagination uses `cursor` (offset) + `k` (page size); fetch `k + 1` to set `has_more`.

**Database**
- SQLAlchemy is used via raw SQL (`sqlalchemy.text`) and `engine.begin()` context.
- Keep SQL parameterized; avoid string interpolation.
- When adding queries, return dataclass objects for downstream typing.

**Config + Env**
- Read settings from `api.config` and `.env` (copied from `.env.example`).
- Avoid hardcoding base URLs or DB connection strings.

**Logging**
- Logging is configured via `api.logging_config.configure_logging()`.
- Request logging attaches `X-Request-ID` and uses `request_id_ctx`.
- Use `logger = logging.getLogger("api")` for service logs.

### Pipelines (pipelines/ingest_tmdb)
- Use `uv run` to execute scripts with managed dependencies.
- Keep data ingestion and embedding logic separate (`ingest.py` vs `embed_movies.py`).
- Prefer explicit column names and types when writing to Postgres.

## Notes for Agents
- There are no Cursor/Copilot rules in this repo.
- There is no existing `AGENTS.md`; this file is the canonical reference.
- If you add new commands (lint/test/build), update this file.
