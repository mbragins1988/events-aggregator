# app/infrastructure/events_provider_client.py
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import date

logger = logging.getLogger(__name__)


class EventsProviderClient:
    """Клиент для Events Provider API"""

    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def get_events_page(
        self, changed_at: date, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить ОДНУ страницу событий.

        Args:
            changed_at: дата изменений (YYYY-MM-DD)
            cursor: курсор для пагинации (опционально)

        Returns:
            {
                "next": "url следующей страницы или null",
                "previous": "url предыдущей страницы или null",
                "results": [список событий]
            }
        """
        params = {"changed_at": changed_at.isoformat()}
        url = f"{self._base_url}/api/events/"
        if cursor:
            params["cursor"] = cursor
        try:
            logger.info("Попытка получения мероприятий на сервисе")
            response = await self._client.get(
                url, params=params, headers={"x-api-key": self._api_key}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Events API HTTP ошибка {e.response.status_code}: {e}")
            return {"next": None, "previous": None, "results": []}
        except httpx.RequestError as e:
            logger.error(f"Events API ошибка подключения: {e}")
            return {"next": None, "previous": None, "results": []}

    async def get_all_events(self, changed_at: date) -> List[Dict[str, Any]]:
        """
        Получить ВСЕ события (обходит пагинацию).
        Именно этот метод используем в синхронизации.
        """
        all_events = []
        cursor = None

        while True:
            page = await self.get_events_page(changed_at, cursor)
            all_events.extend(page["results"])

            next_url = page.get("next")
            if not next_url:
                break

            # Извлекаем курсор из URL следующей страницы
            if "cursor=" in next_url:
                cursor = next_url.split("cursor=")[-1]
            else:
                break

        logger.info(f"Получено {len(all_events)} событий из API")
        return all_events

    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получить конкретное событие"""
        url = f"{self._base_url}/api/events/{event_id}/"
        try:
            response = await self._client.get(url, headers={"x-api-key": self._api_key})

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Events API ошибка: {response.status_code}")
                return None

        except httpx.RequestError as e:
            logger.error(f"Events API ошибка подключения: {e}")
            return None

    async def get_seats(self, event_id: str) -> List[str]:
        """Получить свободные места на событии"""
        url = f"{self._base_url}/api/events/{event_id}/seats/"
        try:
            response = await self._client.get(url, headers={"x-api-key": self._api_key})

            if response.status_code == 200:
                data = response.json()
                return data.get("seats", [])
            else:
                logger.error(f"Events API ошибка: {response.status_code}")
                return []

        except httpx.RequestError as e:
            logger.error(f"Events API ошибка подключения: {e}")
            return []

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> Optional[str]:
        """
        Зарегистрироваться на событие.

        Returns:
            ticket_id или None в случае ошибки
        """
        url = f"{self._base_url}/api/events/{event_id}/register/"
        try:
            response = await self._client.post(
                url,
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
                headers={
                    "x-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:  # было 201
                data = response.json()
                return data.get("ticket_id")
            else:
                logger.error(
                    f"Events API ошибка: {response.status_code} - {response.text}"
                )
                return None

        except httpx.RequestError as e:
            logger.error(f"Events API ошибка подключения: {e}")
            return None

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        """Отменить регистрацию"""
        url = f"{self._base_url}/api/events/{event_id}/unregister/"
        try:
            # Используем общий метод request с DELETE и json данными
            response = await self._client.request(
                method="DELETE",
                url=url,
                json={"ticket_id": ticket_id},  # ← теперь json работает!
                headers={
                    "x-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
            else:
                logger.error(
                    f"Events API ошибка: {response.status_code} - {response.text}"
                )
                return False

        except httpx.RequestError as e:
            logger.error(f"Events API ошибка подключения: {e}")
            return False

    async def close(self):
        """Закрыть клиент"""
        await self._client.aclose()
