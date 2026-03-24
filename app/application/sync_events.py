import logging
from datetime import datetime, timezone

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.db_schema import events_tbl
from app.infrastructure.events_paginator import EventsPaginator
from app.infrastructure.events_provider_client import EventsProviderClient
from app.infrastructure.sync_metadata_repository import SyncMetadataRepository

logger = logging.getLogger(__name__)


class SyncEventsService:
    """Сервис для синхронизации событий"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.metadata_repo = SyncMetadataRepository(session)
        self.client = EventsProviderClient(
            base_url=settings.CATALOG_BASE_URL, api_key=settings.API_TOKEN
        )

    async def sync(self) -> int:
        """Запустить инкрементальную синхронизацию"""
        logger.info("Starting incremental sync...")

        # 1. Получаем текущие метаданные синхронизации
        metadata = await self.metadata_repo.get()
        changed_at_param = metadata.get_changed_at_param()

        logger.info(f"Syncing events changed after: {changed_at_param}")

        try:
            # 2. Используем пагинатор для обхода всех страниц
            changed_at = datetime.fromisoformat(changed_at_param).date()
            paginator = EventsPaginator(self.client, changed_at)

            # 3. Обрабатываем события
            max_changed_at = metadata.last_changed_at or datetime(
                2000, 1, 1, tzinfo=timezone.utc
            )
            count = 0

            async for event_data in paginator:
                # Определяем changed_at события
                event_changed_at = datetime.fromisoformat(
                    event_data.get("changed_at", event_data["created_at"]).replace(
                        "Z", "+00:00"
                    )
                )

                # Обновляем максимальную дату
                if event_changed_at > max_changed_at:
                    max_changed_at = event_changed_at

                # Сохраняем событие (insert или update)
                await self._save_event(event_data)
                count += 1

                if count % 10 == 0:
                    await self.session.commit()
                    logger.info("Saved %d events...", count)

            await self.session.commit()

            # 4. Обновляем метаданные
            metadata.update_after_sync(
                max_changed_at=max_changed_at, total_events=count, status="success"
            )
            await self.metadata_repo.update(metadata)

            logger.info("Sync completed. Total new/updated: %d events", count)
            logger.info("Last changed_at: %s", max_changed_at)

            return count

        except Exception as e:
            error_msg = str(e)
            logger.error("Sync failed: %s", error_msg, exc_info=True)

            # Обновляем метаданные с ошибкой
            metadata.update_after_sync(
                max_changed_at=metadata.last_changed_at
                or datetime(2000, 1, 1, tzinfo=timezone.utc),
                total_events=0,
                status="error",
                error=error_msg,
            )
            await self.metadata_repo.update(metadata)

            raise
        finally:
            await self.client.close()

    async def _save_event(self, event_data: dict) -> None:
        """Сохранить одно событие (insert или update)"""
        existing = await self.session.execute(
            select(events_tbl).where(events_tbl.c.id == event_data["id"])
        )
        existing_row = existing.scalar_one_or_none()

        if existing_row:
            # Обновляем
            stmt = (
                update(events_tbl)
                .where(events_tbl.c.id == event_data["id"])
                .values(
                    name=event_data["name"],
                    place_id=event_data["place"]["id"],
                    place_name=event_data["place"]["name"],
                    place_city=event_data["place"]["city"],
                    place_address=event_data["place"]["address"],
                    place_seats_pattern=event_data["place"]["seats_pattern"],
                    event_time=datetime.fromisoformat(
                        event_data["event_time"].replace("Z", "+00:00")
                    ),
                    registration_deadline=datetime.fromisoformat(
                        event_data["registration_deadline"].replace("Z", "+00:00")
                    ),
                    status=event_data["status"],
                    number_of_visitors=event_data.get("number_of_visitors", 0),
                )
            )
        else:
            # Вставляем новое
            stmt = insert(events_tbl).values(
                id=event_data["id"],
                name=event_data["name"],
                place_id=event_data["place"]["id"],
                place_name=event_data["place"]["name"],
                place_city=event_data["place"]["city"],
                place_address=event_data["place"]["address"],
                place_seats_pattern=event_data["place"]["seats_pattern"],
                event_time=datetime.fromisoformat(
                    event_data["event_time"].replace("Z", "+00:00")
                ),
                registration_deadline=datetime.fromisoformat(
                    event_data["registration_deadline"].replace("Z", "+00:00")
                ),
                status=event_data["status"],
                number_of_visitors=event_data.get("number_of_visitors", 0),
                created_at=datetime.fromisoformat(
                    event_data["created_at"].replace("Z", "+00:00")
                ),
                status_changed_at=datetime.fromisoformat(
                    event_data["status_changed_at"].replace("Z", "+00:00")
                ),
            )

        await self.session.execute(stmt)
