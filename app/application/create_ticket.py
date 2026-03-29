from datetime import datetime, timezone
from typing import Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import (
    EventNotFoundError,
    EventNotPublishedError,
    RegistrationDeadlinePassedError,
    SeatNotAvailableError,
    TicketCreationError,
)
from app.domain.models import Event
from app.infrastructure.outbox_repository import OutboxRepository


class EventRepository(Protocol):
    """Интерфейс репозитория событий"""

    async def get_by_id(self, event_id: str) -> Optional[Event]: ...


class EventsProviderClient(Protocol):
    """Интерфейс клиента внешнего API"""

    async def get_seats(self, event_id: str) -> list[str]: ...

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> Optional[str]: ...

    async def close(self): ...


class TicketRepository(Protocol):
    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ): ...


class CreateTicketUseCase:
    """
    Бизнес-логика регистрации на событие.
    """

    def __init__(
        self,
        event_repo: EventRepository,
        api_client: EventsProviderClient,
        ticket_repo: TicketRepository,
        session: AsyncSession,
    ):
        self.event_repo = event_repo
        self.api_client = api_client
        self.ticket_repo = ticket_repo
        self.session = session  # ← сохраняем для outbox

    async def execute(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        """
        Выполнить регистрацию на событие.
        """
        # 1. Проверяем существование события
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise EventNotFoundError(f"Event with id {event_id} not found")

        # 2. Проверяем статус
        if not event.is_published():
            raise EventNotPublishedError(
                f"Event {event_id} is not published (status: {event.status})"
            )

        # 3. Проверяем дедлайн
        now = datetime.now(timezone.utc)
        if now > event.registration_deadline:
            raise RegistrationDeadlinePassedError(
                f"Registration deadline passed for event {event_id}"
            )

        # 4. Проверяем доступность места
        available_seats = await self.api_client.get_seats(event_id)
        if seat not in available_seats:
            raise SeatNotAvailableError(
                f"Seat {seat} is not available for event {event_id}"
            )

        # 5. Регистрируем через API
        ticket_id = await self.api_client.register(
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        if not ticket_id:
            raise TicketCreationError(f"Failed to create ticket for event {event_id}")

        # 6. Сохраняем билет в своей БД
        await self.ticket_repo.create(
            ticket_id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        # 7. Сохраняем в outbox для отправки уведомления
        outbox_repo = OutboxRepository(self.session)
        await outbox_repo.create(
            event_type="ticket_created",
            payload={
                "ticket_id": ticket_id,
                "event_id": event_id,
                "event_name": event.name,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )

        return ticket_id
