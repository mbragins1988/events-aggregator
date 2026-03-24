# app/main.py
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI

from app.config import settings
from app.presentation.api import router
from app.presentation.sync_worker import run_scheduled_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

sync_task = None
logger.info(f"SENTRY_DSN starts with http: {str(settings.SENTRY_DSN)}")
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment="production",
    release="1.0.0",
    traces_sample_rate=1.0,
)


async def monitor_worker(name: str, worker_func):
    """Мониторинг состояния воркера"""
    logger.info(f"Запуск воркера '{name}'")
    try:
        await worker_func
    except asyncio.CancelledError:
        logger.info(f"Воркер '{name}' отменен")
    except Exception as e:
        logger.error(f"Ошибка воркера '{name}': {e}", exc_info=True)
    finally:
        logger.info(f"Воркер '{name}' остановлен")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global sync_task

    # Запускаем фоновую синхронизацию
    logger.info("Запуск воркера scheduled sync")
    sync_task = asyncio.create_task(
        monitor_worker("sync", run_scheduled_sync(interval_hours=24))
    )
    logger.info("Запущен запланированный обработчик синхронизации")

    yield

    # Останавливаем воркер при завершении
    logger.info("Остановка запланированного синхронизирующего процесса")
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    logger.info("Воркер остановлен")


app = FastAPI(title="Events Aggregator", lifespan=lifespan)

app.include_router(router)


@app.get("/")
async def root():
    return {"service": "Events Aggregator", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/workers")
async def workers_health():
    """Проверка статуса воркеров"""
    if sync_task and not sync_task.done():
        return {"sync_worker": "running"}
    else:
        return {"sync_worker": "stopped"}
