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

    async def get_result(self, key: str) -> Optional[dict]:
        """Получить сохраненный результат по ключу идемпотентности"""
        query = select(idempotency_keys_tbl).where(idempotency_keys_tbl.c.key == key)
        result = await self.session.execute(query)
        row = result.first()

        if row:
            return {
                "ticket_id": row.ticket_id,
                "event_id": row.event_id,
            }
        return None

    async def save_result(self, key: str, ticket_id: str, event_id: str) -> bool:
        """
        Сохранить результат успешной операции.
        Returns: True если сохранено, False если ключ уже существует (конфликт)
        """
        try:
            stmt = insert(idempotency_keys_tbl).values(
                key=key,
                ticket_id=ticket_id,
                event_id=event_id,
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"Idempotency key saved: {key} -> ticket {ticket_id}")
            return True
        except IntegrityError:
            await self.session.rollback()
            logger.warning(f"Idempotency key already exists: {key}")
            return False
