import logging
from typing import Optional

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db_schema import idempotency_keys_tbl

logger = logging.getLogger(__name__)


class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_result(
        self,
        key: str,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> bool:
        """Сохранить результат успешной операции"""
        try:
            stmt = insert(idempotency_keys_tbl).values(
                key=key,
                ticket_id=ticket_id,
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
            await self.session.execute(stmt)
            await self.session.commit()
            return True
        except IntegrityError:
            await self.session.rollback()
            return False

    async def get_result(self, key: str) -> Optional[dict]:
        """Получить сохраненный результат по ключу"""
        query = select(idempotency_keys_tbl).where(idempotency_keys_tbl.c.key == key)
        result = await self.session.execute(query)
        row = result.first()

        if row:
            return {
                "ticket_id": row.ticket_id,
                "event_id": row.event_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "email": row.email,
                "seat": row.seat,
            }
        return None
