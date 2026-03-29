# app/background/outbox_worker.py
import asyncio
import logging

from app.database import AsyncSessionLocal
from app.infrastructure.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Воркер для обработки outbox событий"""

    def __init__(self, interval_seconds: int = 10, max_attempts: int = 10):
        self.interval_seconds = interval_seconds
        self.max_attempts = max_attempts
        self._running = False
        self._task = None

    async def _process_one_event(self, event):
        """Обработать одно outbox событие (пока заглушка)"""
        logger.info(f"Processing outbox event: {event.id}, type: {event.event_type}")

        # TODO: Здесь будет отправка в Capashino
        # Пока просто логируем
        logger.info(f"Event payload: {event.payload}")

        # Имитация успешной обработки
        # В реальности здесь будет вызов Capashino API
        return True

    async def _run(self):
        """Основной цикл воркера"""
        logger.info(
            f"Outbox worker started. Interval: {self.interval_seconds}s, Max attempts: {self.max_attempts}"
        )

        while self._running:
            try:
                async with AsyncSessionLocal() as session:
                    repo = OutboxRepository(session)
                    pending = await repo.get_pending(limit=10)

                    if pending:
                        logger.info(f"Found {len(pending)} pending outbox events")

                        for event in pending:
                            # Проверяем, не превышен ли лимит попыток
                            if event.attempts >= self.max_attempts:
                                logger.error(
                                    f"Event {event.id} exceeded max attempts ({self.max_attempts})"
                                )
                                await repo.mark_final_failed(
                                    event.id,
                                    f"Exceeded max attempts: {self.max_attempts}",
                                )
                                continue

                            try:
                                success = await self._process_one_event(event)

                                if success:
                                    await repo.mark_sent(event.id)
                                    logger.info(
                                        f"Outbox event {event.id} processed successfully"
                                    )
                                else:
                                    await repo.mark_failed(
                                        event.id, "Processing failed"
                                    )
                                    logger.warning(
                                        f"Outbox event {event.id} failed, will retry"
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
        """Запустить воркер"""
        if self._running:
            logger.warning("Outbox worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Outbox worker started")

    async def stop(self):
        """Остановить воркер"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Outbox worker stopped")


# Создаем глобальный экземпляр воркера
outbox_worker = OutboxWorker(
    interval_seconds=10,  # 10 секунд
    max_attempts=10,  # 10 попыток
)
