import logging

import httpx

logger = logging.getLogger(__name__)


class CapashinoClient:
    """Клиент для Notification-сервиса Capashino"""

    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        """Вход в контекстный менеджер"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        await self.close()

    async def send_notification(
        self, message: str, reference_id: str, idempotency_key: str
    ) -> bool:
        """Отправить уведомление в Capashino"""
        url = f"{self._base_url}/api/notifications"

        payload = {
            "message": message,
            "reference_id": reference_id,
            "idempotency_key": idempotency_key,
        }

        try:
            response = await self._client.post(
                url,
                json=payload,
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 201:
                logger.info(f"Notification sent successfully: {reference_id}")
                return True
            else:
                logger.error(
                    f"Capashino API error:"
                    f"{response.status_code} - {response.text}"
                )
                return False

        except httpx.TimeoutException:
            logger.error(f"Timeout sending notification for {reference_id}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Request error sending notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    async def close(self):
        """Закрыть клиент"""
        await self._client.aclose()
