#!/bin/bash
set -e

export PYTHONUNBUFFERED=1

echo "Applying database migrations"
alembic upgrade head

# Запускаем Celery worker в фоне
echo "Starting Celery worker..."
celery -A app.celery_app worker --loglevel=info --beat &

# Сохраняем PID Celery
CELERY_PID=$!

# Запускаем FastAPI
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

# Если FastAPI упадет, убиваем Celery
trap "kill $CELERY_PID" EXIT
