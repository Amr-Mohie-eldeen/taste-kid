.PHONY: help setup env up build down restart logs logs-api logs-web logs-db ps web api db git-sync

PROJECT_NAME := taste-kid
COMPOSE := docker compose

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Copy .env.example to .env if missing
	@test -f .env || cp .env.example .env

setup: env ## Ensure local env file exists
	@echo "Environment ready."

up: ## Start all services
	$(COMPOSE) up

build: ## Build all service images
	$(COMPOSE) up --build

down: ## Stop and remove containers
	$(COMPOSE) down

restart: ## Restart the stack
	$(COMPOSE) down
	$(COMPOSE) up --build

ps: ## List running services
	$(COMPOSE) ps

logs: ## Tail all logs
	$(COMPOSE) logs -f

logs-api: ## Tail API logs
	$(COMPOSE) logs -f api

logs-web: ## Tail web logs
	$(COMPOSE) logs -f web

logs-db: ## Tail database logs
	$(COMPOSE) logs -f postgres

api: ## Start only API and dependencies
	$(COMPOSE) up api postgres

web: ## Start only web (assumes API running)
	$(COMPOSE) up web

db: ## Start only postgres
	$(COMPOSE) up postgres

lint-api: ## Run linting for API
	$(MAKE) -C apps/api lint

format-api: ## Run formatting for API
	$(MAKE) -C apps/api format

check-api-types: ## Run type checking for API
	$(MAKE) -C apps/api check-types

test-api: ## Run tests for API
	$(MAKE) -C apps/api test

ci-api: ## Run all CI checks for API
	$(MAKE) -C apps/api ci

git-sync: ## Sync main and prune gone branches
	git fetch --prune origin
	git checkout main
	git pull --ff-only
	git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads | \
		while read -r branch track; do \
			if [ "$$branch" = "main" ]; then continue; fi; \
			if [ "$$track" = "[gone]" ]; then git branch -d "$$branch"; fi; \
		done
