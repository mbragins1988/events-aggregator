from datetime import date
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SyncEventsProviderClient:
    """Синхронный клиент для Events Provider API"""

    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url
        self._api_key = api_key
        self._client = httpx.Client(timeout=30.0)

    def get_events_page(
        self, changed_at: date, cursor: str | None = None
    ) -> dict[str, Any]:
        params = {"changed_at": changed_at.isoformat()}
        url = f"{self._base_url}/api/events/"
        if cursor:
            params["cursor"] = cursor

        try:
            logger.info("Попытка получения мероприятий")
            response = self._client.get(
                url, params=params, headers={"x-api-key": self._api_key}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Events API HTTP ошибка %s: %s", e.response.status_code, e
            )
            return {"next": None, "previous": None, "results": []}
        except httpx.RequestError as e:
            logger.error("Events API ошибка подключения: %s", e)
            return {"next": None, "previous": None, "results": []}

    def get_all_events(self, changed_at: date) -> list[dict[str, Any]]:
        all_events = []
        cursor = None

        while True:
            page = self.get_events_page(changed_at, cursor)
            all_events.extend(page["results"])

            next_url = page.get("next")
            if not next_url:
                break

            if "cursor=" in next_url:
                cursor = next_url.split("cursor=")[-1]
            else:
                break

        logger.info("Получено %d событий из API", len(all_events))
        return all_events

    def close(self):
        self._client.close()
