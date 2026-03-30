import asyncio
import logging

from app.application.sync_events import SyncEventsService
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_scheduled_sync(interval_hours: int = 24):
    """Фоновый воркер для синхронизации раз в сутки"""
    interval_seconds = interval_hours * 3600
    logger.info(f"Sync worker started. Interval: {interval_hours} hours")

    while True:
        try:
            logger.info("Running scheduled sync...")
            async with AsyncSessionLocal() as session:
                service = SyncEventsService(session)
                count = await service.sync()
                logger.info(
                    f"Scheduled sync completed. {count} events updated."
                )
        except Exception as e:
            logger.error(f"Scheduled sync failed: {e}", exc_info=True)

        logger.info(f"Next sync in {interval_hours} hours")
        await asyncio.sleep(interval_seconds)
