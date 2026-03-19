# app/application/sync_events.py
import logging
from datetime import date, datetime
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.events_provider_client import EventsProviderClient
from app.infrastructure.db_schema import events_tbl
from app.config import settings

logger = logging.getLogger(__name__)


class SyncEventsService:
    """Сервис для синхронизации событий"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = EventsProviderClient(
            base_url=settings.CATALOG_BASE_URL,
            api_key=settings.API_TOKEN
        )
    
    async def sync(self) -> int:
        """Запустить синхронизацию"""
        logger.info(f"Синхронизация клиента {self.client}")
        
        # Получаем все события с 2000-01-01
        events_data = await self.client.get_all_events(changed_at=date(2000, 1, 1))
        logger.info(f"Получено {len(events_data)} событий из API")
        
        # Сохраняем в БД
        count = 0
        for event_data in events_data:
            # Проверяем, есть ли уже такое событие
            existing = await self.session.execute(
                select(events_tbl).where(events_tbl.c.id == event_data["id"])
            )
            if existing.scalar_one_or_none():
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
                        event_time=datetime.fromisoformat(event_data["event_time"].replace("Z", "+00:00")),
                        registration_deadline=datetime.fromisoformat(event_data["registration_deadline"].replace("Z", "+00:00")),
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
                    event_time=datetime.fromisoformat(event_data["event_time"].replace("Z", "+00:00")),
                    registration_deadline=datetime.fromisoformat(event_data["registration_deadline"].replace("Z", "+00:00")),
                    status=event_data["status"],
                    number_of_visitors=event_data.get("number_of_visitors", 0),
                    created_at=datetime.fromisoformat(event_data["created_at"].replace("Z", "+00:00")),
                    status_changed_at=datetime.fromisoformat(event_data["status_changed_at"].replace("Z", "+00:00")),
                )
            
            await self.session.execute(stmt)
            count += 1
            
            if count % 10 == 0:
                await self.session.commit()
                logger.info(f"Saved {count} events...")
        
        await self.session.commit()
        await self.client.close()
        logger.info(f"Sync completed. Total: {count} events")
        
        return count
