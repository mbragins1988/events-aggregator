# app/main.py
import logging
import sys

from fastapi import FastAPI

from app.celery_app import celery_app
from app.presentation.api import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Events Aggregator")

app.include_router(router)


@app.get("/")
async def root():
    return {"service": "Events Aggregator", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/celery/status")
async def celery_status():
    """
    Проверка статуса Celery воркера.
    """
    try:
        # Отправляем тестовую задачу
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            workers = list(stats.keys())
            return {
                "status": "running",
                "workers": workers,
                "worker_count": len(workers),
            }
        else:
            return {"status": "no_workers", "message": "No Celery workers running"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
