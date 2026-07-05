# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Base image with uv preinstalled (Astral). Fast, reproducible installs.
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# ---------------------------------------------------------------------------
# Dependencies layer (cached unless pyproject/lock change)
# ---------------------------------------------------------------------------
COPY pyproject.toml ./
COPY uv.lock* ./
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev || uv sync --no-install-project

# ---------------------------------------------------------------------------
# Application layer
# ---------------------------------------------------------------------------
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev || uv sync

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
