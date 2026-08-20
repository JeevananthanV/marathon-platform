#!/bin/sh
set -e

echo "Running safe database migrations..."
alembic upgrade head

echo "Starting Marathon FastAPI application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2}
