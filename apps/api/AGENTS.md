# apps/api AGENTS

FastAPI + Postgres/pgvector backend.

## Commands
- From repo root: `make ci-api` (lint + types + tests)
- From `apps/api`: `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`, `uv run pytest`

## Where To Look
- App setup, middleware, exception mapping: `apps/api/src/api/main.py`
- HTTP endpoints + response models (all under `/v1`): `apps/api/src/api/v1/main.py`
- Recommendations/feed: `apps/api/src/api/users/recommendations.py`, `apps/api/src/api/users/queue.py`
- Heuristic scoring: `apps/api/src/api/rerank/scorer.py`
- Config/env: `apps/api/src/api/config.py`
- Shared schema bootstrap: `infra/db/init.sql`

## Conventions
- Response envelope: `{"data": ..., "meta": ...}`
- Offset pagination: fetch `k + 1` to compute `has_more`.
- DB access: `sqlalchemy.text` + bound params inside `engine.begin()`.

## Testing Notes
- Tests use `testcontainers`; Docker must be running.
- Integration DB image: `pgvector/pgvector:pg16`.

## Anti-Patterns
- No SQL string interpolation.
- Avoid drive-by refactors while fixing bugs.
- Don’t bypass the response envelope in new routes.
