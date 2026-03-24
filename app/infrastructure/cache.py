# app/infrastructure/cache.py
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """Простой кэш с временем жизни (TTL)"""

    def __init__(self, ttl_seconds: int = 30):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша, если оно не истекло"""
        if key in self._cache:
            item = self._cache[key]
            if time.time() - item["timestamp"] < self.ttl:
                logger.debug(f"Cache HIT for {key}")
                return item["value"]
            else:
                logger.debug(f"Cache EXPIRED for {key}")
                del self._cache[key]
        logger.debug(f"Cache MISS for {key}")
        return None

    def set(self, key: str, value: Any):
        """Сохранить значение в кэш"""
        self._cache[key] = {"value": value, "timestamp": time.time()}
        logger.debug(f"Cache SET for {key}")

    def clear(self):
        """Очистить кэш"""
        self._cache.clear()
        logger.debug("Cache CLEARED")


# Создаем глобальный экземпляр кэша для мест
seats_cache = TTLCache(ttl_seconds=30)
