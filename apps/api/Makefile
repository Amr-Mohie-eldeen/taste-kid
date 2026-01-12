.PHONY: lint format check-types test ci sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

check-types:
	uv run pyright

test:
	uv run pytest

ci: lint check-types test

sync:
	uv sync
