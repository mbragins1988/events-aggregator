# app/main.py
import asyncio
from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from app.presentation.api import router
from app.presentation.sync_worker import run_scheduled_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Запускаем фоновую синхронизацию
    logger.info("Starting scheduled sync worker...")
    sync_task = asyncio.create_task(run_scheduled_sync(interval_hours=24))

    yield

    # Останавливаем воркер при завершении
    logger.info("Stopping sync worker...")
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    logger.info("Sync worker stopped")


app = FastAPI(title="Events Aggregator", lifespan=lifespan)
app.add_middleware(SentryAsgiMiddleware)
app.include_router(router)


@app.get("/")
async def root():
    return {"service": "Events Aggregator", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
