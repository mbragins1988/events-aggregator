# app/infrastructure/ticket_repository.py
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db_schema import tickets_tbl


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ):
        """Сохранить информацию о билете"""
        stmt = tickets_tbl.insert().values(
            id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_by_id(self, ticket_id: str) -> Optional[dict]:
        """Получить билет по ID"""
        query = select(tickets_tbl).where(tickets_tbl.c.id == ticket_id)
        result = await self.session.execute(query)
        row = result.first()
        if not row:
            return None

        # Исправление: преобразуем Row в словарь правильно
        return {
            "id": row.id,
            "event_id": row.event_id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "email": row.email,
            "seat": row.seat,
            "created_at": row.created_at,
        }

    async def delete(self, ticket_id: str):
        """Удалить билет"""
        stmt = tickets_tbl.delete().where(tickets_tbl.c.id == ticket_id)
        await self.session.execute(stmt)
        await self.session.commit()
