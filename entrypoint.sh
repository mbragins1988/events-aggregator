#!/bin/bash
set -e

export PYTHONUNBUFFERED=1

echo "Applying database migrations"
alembic upgrade head

# Запускаем FastAPI
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
