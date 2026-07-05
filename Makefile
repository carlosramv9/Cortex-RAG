.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test check run up down migrate revision contracts

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (incl. dev) via uv
	uv sync --extra dev

lint: ## Run ruff linter
	uv run ruff check app tests

format: ## Format code with ruff
	uv run ruff format app tests

typecheck: ## Run mypy
	uv run mypy app

test: ## Run tests
	uv run pytest

contracts: ## Verify Clean Architecture import contracts
	uv run lint-imports

check: lint typecheck contracts test ## Run all quality gates

run: ## Run API locally with reload
	uv run uvicorn app.main:app --reload

up: ## Start the full stack
	docker compose up --build

down: ## Stop the stack
	docker compose down

migrate: ## Apply DB migrations
	uv run alembic upgrade head

revision: ## Create a new migration (usage: make revision m="message")
	uv run alembic revision --autogenerate -m "$(m)"
