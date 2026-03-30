# app/background/outbox_worker.py
import asyncio
import logging

from app.config import settings
from app.database import AsyncSessionLocal
from app.infrastructure.capashino_client import CapashinoClient
from app.infrastructure.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Воркер для обработки outbox событий"""

    def __init__(self, interval_seconds: int = 10):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task = None

    async def _send_notification(self, event) -> bool:
        """Отправить уведомление в Capashino"""
        payload = event.payload
        event_name = payload.get("event_name", "мероприятие")
        message = f"Вы успешно зарегистрированы на мероприятие - {event_name}"
        reference_id = payload.get("ticket_id")
        idempotency_key = event.id  # используем outbox event id

        async with CapashinoClient(
            base_url=settings.CAPASHINO_BASE_URL, api_key=settings.API_TOKEN
        ) as client:
            return await client.send_notification(
                message=message,
                reference_id=reference_id,
                idempotency_key=idempotency_key,
            )

    async def _process_one_event(self, event) -> bool:
        """Обработать одно outbox событие"""
        logger.info(f"Processing outbox event: {event.id}")

        if event.event_type == "ticket_created":
            return await self._send_notification(event)
        else:
            logger.warning(f"Unknown event type: {event.event_type}")
            return True

    async def _run(self):
        """Основной цикл воркера"""
        logger.info(f"Outbox worker started. Interval: {self.interval_seconds}s")

        while self._running:
            try:
                async with AsyncSessionLocal() as session:
                    repo = OutboxRepository(session)
                    pending = await repo.get_pending(limit=10)

                    if pending:
                        logger.info(f"Found {len(pending)} pending outbox events")

                        for event in pending:
                            try:
                                success = await self._process_one_event(event)

                                if success:
                                    await repo.mark_sent(event.id)
                                    logger.info(f"Outbox event {event.id} sent")
                                else:
                                    await repo.mark_failed(
                                        event.id, "Capashino API returned error"
                                    )
                                    logger.warning(
                                        f"Outbox event {event.id} failed, will retry later"
                                    )

                            except Exception as e:
                                error_msg = str(e)
                                logger.error(
                                    f"Error processing outbox event {event.id}: {error_msg}"
                                )
                                await repo.mark_failed(event.id, error_msg)
                    else:
                        logger.debug("No pending outbox events")

            except Exception as e:
                logger.error(f"Outbox worker error: {e}", exc_info=True)

            await asyncio.sleep(self.interval_seconds)

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Outbox worker started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Outbox worker stopped")


outbox_worker = OutboxWorker(interval_seconds=settings.OUTBOX_INTERVAL_SECONDS)
