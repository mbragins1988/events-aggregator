import logging
from datetime import date
from typing import Any, Dict, Optional

from app.infrastructure.events_provider_client import EventsProviderClient

logger = logging.getLogger(__name__)


class EventsPaginator:
    """
    Итератор для обхода всех страниц событий из Events Provider API.
    Использует cursor-based пагинацию.
    """

    def __init__(self, client: EventsProviderClient, changed_at: date):
        self._client = client
        self._changed_at = changed_at
        self._cursor: Optional[str] = None
        self._current_page: Optional[Dict[str, Any]] = None
        self._current_index: int = 0
        self._done: bool = False

    def __aiter__(self) -> "EventsPaginator":
        """Возвращает себя как асинхронный итератор"""
        return self

    async def __anext__(self) -> Dict[str, Any]:
        """
        Возвращает следующее событие.

        Raises:
            StopAsyncIteration: когда события закончились
        """
        if self._done:
            raise StopAsyncIteration

        # Если текущая страница пуста или мы дошли до конца страницы
        if self._current_page is None or self._current_index >= len(
            self._current_page.get("results", [])
        ):
            # Загружаем следующую страницу
            await self._load_next_page()

            # Если после загрузки нет событий — завершаем
            if self._done:
                raise StopAsyncIteration

        # Возвращаем текущее событие и двигаем индекс
        event = self._current_page["results"][self._current_index]
        self._current_index += 1
        return event

    async def _load_next_page(self) -> None:
        """Загружает следующую страницу"""
        page = await self._client.get_events_page(self._changed_at, self._cursor)

        results = page.get("results", [])

        if not results:
            # Нет событий — завершаем
            self._done = True
            self._current_page = None
            return

        self._current_page = page
        self._current_index = 0

        # Обновляем курсор для следующей страницы
        next_url = page.get("next")
        if next_url and "cursor=" in next_url:
            self._cursor = next_url.split("cursor=")[-1]
        else:
            # Нет следующей страницы
            self._cursor = None

        logger.debug(
            f"Загружена страница с {len(results)} событиями, cursor={self._cursor}"
        )

    async def get_all(self) -> list:
        """
        Получить все события как список.
        """
        all_events = []
        async for event in self:
            all_events.append(event)
        return all_events
