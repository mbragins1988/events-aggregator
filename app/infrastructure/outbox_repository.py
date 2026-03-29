from datetime import datetime
import logging
from typing import List
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import OutboxEvent
from app.infrastructure.db_schema import outbox_tbl

logger = logging.getLogger(__name__)


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event_type: str, payload: dict) -> str:
        """Создать запись в outbox"""
        event_id = str(uuid.uuid4())
        stmt = outbox_tbl.insert().values(
            id=event_id,
            event_type=event_type,
            payload=payload,
            status="pending",
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.debug(f"Outbox event created: {event_id}")
        return event_id

    async def get_pending(self, limit: int = 10) -> List[OutboxEvent]:
        """Получить неотправленные события"""
        query = (
            select(outbox_tbl)
            .where(outbox_tbl.c.status == "pending")
            .order_by(outbox_tbl.c.created_at)
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        events = []
        for row in rows:
            events.append(
                OutboxEvent(
                    id=row.id,
                    event_type=row.event_type,
                    payload=row.payload,
                    status=row.status,
                    last_error=row.last_error,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )
        return events

    async def mark_sent(self, event_id: str):
        """Пометить событие как отправленное"""
        stmt = (
            update(outbox_tbl)
            .where(outbox_tbl.c.id == event_id)
            .values(status="sent", updated_at=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.debug(f"Outbox event marked as sent: {event_id}")

    async def mark_failed(self, event_id: str, error: str):
        """Пометить событие как неудачное (остается pending)"""
        stmt = (
            update(outbox_tbl)
            .where(outbox_tbl.c.id == event_id)
            .values(last_error=error, updated_at=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.warning(f"Outbox event failed: {event_id}, error: {error}")
