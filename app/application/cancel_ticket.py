from datetime import datetime, timezone
from typing import Optional, Protocol

from app.domain.exceptions import (
    EventAlreadyPassedError,
    EventNotFoundError,
    TicketNotFoundError,
)
from app.domain.models import Event


class EventRepository(Protocol):
    """Интерфейс репозитория событий"""

    async def get_by_id(self, event_id: str) -> Event | None: ...


class EventsProviderClient(Protocol):
    """Интерфейс клиента внешнего API"""

    async def unregister(self, event_id: str, ticket_id: str) -> bool: ...

    async def close(self): ...


class TicketRepository(Protocol):
    async def get_by_id(self, ticket_id: str) -> Optional[dict]: ...

    async def delete(self, ticket_id: str): ...


class CancelTicketUseCase:
    def __init__(
        self,
        ticket_repo: TicketRepository,
        event_repo: EventRepository,
        api_client: EventsProviderClient,
    ):
        self.ticket_repo = ticket_repo
        self.event_repo = event_repo
        self.api_client = api_client

    async def execute(self, ticket_id: str) -> bool:
        # 1. Находим билет в своей БД
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")

        # 2. Проверяем событие
        event = await self.event_repo.get_by_id(ticket["event_id"])
        if not event:
            raise EventNotFoundError(f"Event {ticket['event_id']} not found")

        # 3. Проверяем, не прошло ли событие (ИСПРАВЛЕНО)
        if datetime.now(timezone.utc) > event.event_time:
            raise EventAlreadyPassedError("Cannot cancel registration for past event")

        # 4. Отменяем через API
        success = await self.api_client.unregister(ticket["event_id"], ticket_id)

        if not success:
            return False

        # 5. Удаляем из своей БД
        await self.ticket_repo.delete(ticket_id)

        return True
