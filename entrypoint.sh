#!/bin/bash
set -e

export PYTHONUNBUFFERED=1 
echo "Applying database migrations"
alembic upgrade head

echo "Starting FastAPI application with embedded workers..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
