from datetime import datetime, timezone
from typing import Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import (
    EventNotFoundError,
    EventNotPublishedError,
    IdempotencyConflictError,
    RegistrationDeadlinePassedError,
    SeatNotAvailableError,
    TicketCreationError,
)
from app.domain.models import Event
from app.infrastructure.idempotency_repository import IdempotencyRepository
from app.infrastructure.outbox_repository import OutboxRepository


class EventRepository(Protocol):
    async def get_by_id(self, event_id: str) -> Optional[Event]: ...


class EventsProviderClient(Protocol):
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
        self.session = session
        self.idempotency_repo = IdempotencyRepository(session)
        self.outbox_repo = OutboxRepository(session)

    async def execute(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """
        Выполнить регистрацию с поддержкой идемпотентности.
        """
        # 1. Если передан ключ идемпотентности — проверяем, не обрабатывали ли уже
        if idempotency_key:
            existing = await self.idempotency_repo.get_result(idempotency_key)

            if existing:
                # Проверяем ВСЕ данные, а не только event_id
                if (
                    existing["event_id"] != event_id
                    or existing["first_name"] != first_name
                    or existing["last_name"] != last_name
                    or existing["email"] != email
                    or existing["seat"] != seat
                ):
                    # Любое поле отличается → конфликт
                    raise IdempotencyConflictError(
                        f"Idempotency key {idempotency_key} already used with different data"
                    )
                # Все данные совпадают → возвращаем существующий билет
                return existing["ticket_id"]

        # 2. Обычная логика регистрации
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise EventNotFoundError(f"Event with id {event_id} not found")

        if not event.is_published():
            raise EventNotPublishedError(
                f"Event {event_id} is not published (status: {event.status})"
            )

        now = datetime.now(timezone.utc)
        if now > event.registration_deadline:
            raise RegistrationDeadlinePassedError(
                f"Registration deadline passed for event {event_id}"
            )

        available_seats = await self.api_client.get_seats(event_id)
        if seat not in available_seats:
            raise SeatNotAvailableError(
                f"Seat {seat} is not available for event {event_id}"
            )

        ticket_id = await self.api_client.register(
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        if not ticket_id:
            raise TicketCreationError(f"Failed to create ticket for event {event_id}")

        # 3. Сохраняем билет
        await self.ticket_repo.create(
            ticket_id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        # 4. Сохраняем в outbox
        await self.outbox_repo.create(
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

        # 5. Если передан ключ идемпотентности — сохраняем результат
        if idempotency_key:
            saved = await self.idempotency_repo.save_result(
                key=idempotency_key,
                ticket_id=ticket_id,
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
            if not saved:
                # Ключ уже существует (другая операция успела завершиться)
                # Получаем существующий результат и возвращаем его
                existing = await self.idempotency_repo.get_result(idempotency_key)
                if existing:
                    return existing["ticket_id"]
                raise IdempotencyConflictError("Idempotency key conflict")

        return ticket_id
