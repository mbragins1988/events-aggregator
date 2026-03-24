# app/infrastructure/events_paginator.py
from datetime import date
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EventsPaginator:
    def __init__(self, client, changed_at: date):
        self._client = client
        self._changed_at = changed_at
        self._cursor: Optional[str] = None
        self._current_page: Optional[Dict[str, Any]] = None
        self._current_index: int = 0
        self._done: bool = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._done:
            raise StopAsyncIteration

        # Если нет текущей страницы или мы дошли до конца страницы
        if self._current_page is None or self._current_index >= len(
            self._current_page.get("results", [])
        ):
            await self._load_next_page()

            # Если после загрузки страницы нет событий
            if (
                self._done
                or not self._current_page
                or not self._current_page.get("results")
            ):
                self._done = True
                raise StopAsyncIteration

        # Возвращаем текущее событие
        event = self._current_page["results"][self._current_index]
        self._current_index += 1

        # Если это было последнее событие на странице и следующей страницы нет
        if (
            self._current_index >= len(self._current_page.get("results", []))
            and self._cursor is None
        ):
            self._done = True

        return event

    async def _load_next_page(self):
        """Загружает следующую страницу"""
        page = await self._client.get_events_page(self._changed_at, self._cursor)

        results = page.get("results", [])

        if not results:
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
            self._cursor = None

    async def get_all(self) -> list:
        """
        Получить все события как список.
        """
        all_events = []
        async for event in self:
            all_events.append(event)
        return all_events
