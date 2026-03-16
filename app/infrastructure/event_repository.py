# app/infrastructure/event_repository.py
from typing import List, Optional
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db_schema import events_tbl  # импортируем ORM модель
from app.domain.models import Event, EventStatus


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session  # получаем сессию
    
    async def get_all(
        self,
        date_from: Optional[date] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Event]:
        """Получить события из БД"""
        
        # Строим запрос
        query = select(events_tbl)
        
        if date_from:
            query = query.where(
                func.date(events_tbl.event_time) >= date_from
            )
        
        query = query.limit(limit).offset(offset)
        
        # Выполняем запрос (ORM стиль)
        result = await self.session.execute(query)
        db_events = result.scalars().all()  # получаем список ORM моделей
        
        # Конвертируем ORM модели в Domain модели
        events = []
        for db_event in db_events:
            event = Event(
                id=db_event.id,
                name=db_event.name,
                place_id=db_event.place_id,
                place_name=db_event.place_name,
                place_city=db_event.place_city,
                place_address=db_event.place_address,
                place_seats_pattern=db_event.place_seats_pattern,
                event_time=db_event.event_time,
                registration_deadline=db_event.registration_deadline,
                status=EventStatus(db_event.status),
                number_of_visitors=db_event.number_of_visitors,
                status_changed_at=db_event.status_changed_at
            )
            events.append(event)
        
        return events
    
    async def count(self, date_from: Optional[date] = None) -> int:
        """Посчитать количество событий"""
        
        query = select(func.count()).select_from(events_tbl)
        
        if date_from:
            query = query.where(
                func.date(events_tbl.event_time) >= date_from
            )
        
        result = await self.session.execute(query)
        return result.scalar() or 0
