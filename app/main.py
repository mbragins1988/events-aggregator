# app/main.py
import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global sync_task
    
    # Запускаем фоновую синхронизацию
    logger.info("Запуск scheduled_sync...")
    sync_task = asyncio.create_task(run_scheduled_sync(interval_hours=24))
    
    yield
    
    # Останавливаем воркер при завершении
    logger.info("Остановка воркера...")
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    logger.info("Все воркеры отсановлены")


app = FastAPI(
    title="Events Aggregator",
    lifespan=lifespan
)

app.include_router(router)

@app.get("/")
async def root():
    return {"service": "Events Aggregator", "status": "running"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}
