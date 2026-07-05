#!/usr/bin/env sh
set -e

# Run DB migrations before starting the API. Safe no-op when there are no
# pending migrations.
echo "Running database migrations..."
uv run alembic upgrade head || echo "No migrations to apply."

echo "Starting API..."
exec uv run uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
