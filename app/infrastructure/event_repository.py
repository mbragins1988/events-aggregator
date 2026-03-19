from typing import List, Optional
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db_schema import events_tbl
from app.domain.models import Event, EventStatus


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, event_id: str) -> Optional[Event]:
        """Получить событие по ID"""
        query = select(events_tbl).where(events_tbl.c.id == event_id)
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        return Event(
            id=row.id,
            name=row.name,
            place_id=row.place_id,
            place_name=row.place_name,
            place_city=row.place_city,
            place_address=row.place_address,
            place_seats_pattern=row.place_seats_pattern,
            event_time=row.event_time,
            registration_deadline=row.registration_deadline,
            status=row.status,  # теперь строка
            number_of_visitors=row.number_of_visitors,
            created_at=row.created_at,
            status_changed_at=row.status_changed_at
        )
    
    async def get_all(self, date_from: Optional[date] = None, limit: int = 20, offset: int = 0) -> List[Event]:
        query = select(events_tbl)
        
        if date_from:
            query = query.where(
                func.date(events_tbl.c.event_time) >= date_from
            )
        
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        rows = result.all()
        
        events = []
        for row in rows:
            events.append(Event(
                id=row.id,
                name=row.name,
                place_id=row.place_id,
                place_name=row.place_name,
                place_city=row.place_city,
                place_address=row.place_address,
                place_seats_pattern=row.place_seats_pattern,
                event_time=row.event_time,
                registration_deadline=row.registration_deadline,
                status=EventStatus(row.status),
                number_of_visitors=row.number_of_visitors,
                created_at=row.created_at,
                status_changed_at=row.status_changed_at
            ))
        
        return events
    
    async def count(self, date_from: Optional[date] = None) -> int:
        query = select(func.count()).select_from(events_tbl)
        
        if date_from:
            query = query.where(
                func.date(events_tbl.c.event_time) >= date_from
            )
        
        result = await self.session.execute(query)
        return result.scalar() or 0
