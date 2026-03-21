from datetime import datetime, timezone
from typing import Optional, Protocol

from app.domain.models import Event
from app.domain.exceptions import (
    EventNotFoundError,
    EventNotPublishedError,
    RegistrationDeadlinePassedError,
    SeatNotAvailableError,
    TicketCreationError,
)


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

    - Проверяет существование события в локальной БД
    - Проверяет статус события (только для published)
    - Проверяет дедлайн регистрации
    - Проверяет доступность места (через API)
    - Регистрирует через внешнее API
    - Возвращает ticket_id
    """

    def __init__(
        self,
        event_repo: EventRepository,
        api_client: EventsProviderClient,
        ticket_repo: TicketRepository,
    ):
        self.event_repo = event_repo
        self.api_client = api_client
        self.ticket_repo = ticket_repo

    async def execute(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        """
        Выполнить регистрацию на событие.

        Returns:
            str: ticket_id

        Raises:
            EventNotFoundError: если событие не найдено
            EventNotPublishedError: если событие не опубликовано
            RegistrationDeadlinePassedError: если дедлайн прошел
            SeatNotAvailableError: если место недоступно
            TicketCreationError: если API вернул ошибку
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
        now = datetime.now(timezone.utc)  # теперь тоже с часовым поясом
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
            raise TicketCreationError(...)

        # Сохраняем в своей БД
        await self.ticket_repo.create(
            ticket_id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        return ticket_id
