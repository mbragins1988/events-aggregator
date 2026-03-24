# app/application/get_seats.py
from typing import List, Optional, Protocol

from app.domain.exceptions import EventNotFoundError
from app.domain.models import Event
from app.infrastructure.cache import seats_cache


class EventRepository(Protocol):
    """Интерфейс репозитория событий"""

    async def get_by_id(self, event_id: str) -> Optional[Event]: ...


class EventsProviderClient(Protocol):
    """Интерфейс клиента внешнего API"""

    async def get_seats(self, event_id: str) -> List[str]: ...

    async def close(self): ...


class GetSeatsUseCase:
    """
    Бизнес-логика получения свободных мест на событии.

    - Проверяет кэш
    - Проверяет существование события в локальной БД
    - Проверяет статус события (только для published)
    - Запрашивает актуальные места из внешнего API
    - Кэширует результат на 30 секунд
    """

    def __init__(self, event_repo: EventRepository, api_client: EventsProviderClient):
        self.event_repo = event_repo
        self.api_client = api_client

    async def execute(self, event_id: str) -> List[str]:
        """
        Выполнить бизнес-логику получения мест.

        Returns:
            List[str]: список свободных мест

        Raises:
            EventNotFoundError: если событие не найдено в локальной БД
        """
        # 1. Проверяем кэш
        cache_key = f"seats:{event_id}"
        cached_seats = seats_cache.get(cache_key)
        if cached_seats is not None:
            return cached_seats

        # 2. Проверяем существование события в локальной БД
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise EventNotFoundError(f"Event with id {event_id} not found")

        # 3. Бизнес-правило: места доступны только для опубликованных событий
        if not event.is_published():
            # Для неопубликованных событий возвращаем пустой список
            # (согласно документации API)
            seats = []
        else:
            # 4. Запрашиваем актуальные места из внешнего API
            try:
                seats = await self.api_client.get_seats(event_id)
            finally:
                # 5. Всегда закрываем соединение с клиентом
                await self.api_client.close()

        # 6. Сохраняем в кэш (даже пустой список, чтобы не долбить API)
        seats_cache.set(cache_key, seats)

        return seats
