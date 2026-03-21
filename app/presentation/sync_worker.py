import asyncio
import logging
from app.database import AsyncSessionLocal
from app.application.sync_events import SyncEventsService

logger = logging.getLogger(__name__)


async def run_scheduled_sync(interval_hours: int = 24):
    """
    Запустить фоновую синхронизацию с указанным интервалом.

    Args:
        interval_hours: интервал между синхронизациями в часах
    """
    logger.info(f"Начало sync worker. Интервал: {interval_hours} часа")

    while True:
        try:
            logger.info("Запуск запланированной синхронизации...")
            async with AsyncSessionLocal() as session:
                service = SyncEventsService(session)
                count = await service.sync()
                logger.info(f"Синхронизация завершена. {count} мероприятий обновлено.")
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}", exc_info=True)

        # Ждем указанный интервал перед следующей синхронизацией
        wait_seconds = interval_hours * 3600
        await asyncio.sleep(wait_seconds)
