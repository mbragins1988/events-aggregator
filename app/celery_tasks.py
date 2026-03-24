import asyncio
import logging
from app.celery_app import celery_app
from app.database_sync import SyncSessionLocal
from app.application.sync_events import SyncEventsService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.celery_tasks.sync_events_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # 5 минут между повторами
)
def sync_events_task(self):
    """
    Задача синхронизации событий.
    Запускается по расписанию (раз в сутки) или вручную.
    """
    logger.info("Starting scheduled sync task...")
    
    with SyncSessionLocal() as session:
        try:
            service = SyncEventsService(session)
            # В синхронном контексте нужно использовать синхронный клиент
            # или вызывать асинхронный через asyncio.run()
            count = asyncio.run(service.sync())
            
            logger.info("Sync task completed. %d events updated.", count)
            return {"status": "success", "events_synced": count}
            
        except Exception as e:
            logger.error("Sync task failed: %s", e, exc_info=True)
            # Повторяем задачу с задержкой
            raise self.retry(exc=e, countdown=60 * 5)
