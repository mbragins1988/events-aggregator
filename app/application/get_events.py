# app/application/get_events.py
# Бизнес-логика конкретной операции. Координирует работу, но не знает откуда данные.
# Валидирует параметры. Просит репозиторий дать данные. Возвращает результат
from typing import List, Optional, Protocol
from datetime import date
from app.domain.models import Event


class EventRepository(Protocol):
    """Интерфейс (контракт) для репозитория.
    Protocol - способ сказать "нам нужно что-то с такими методами"
    """
    async def get_all(
        self, 
        date_from: Optional[date] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Event]:
        """Получить список событий"""
        ...
    
    async def count(self, date_from: Optional[date] = None) -> int:
        """Получить общее количество"""
        ...


class GetEventsUseCase:
    """Бизнес-логика получения списка событий"""
    
    def __init__(self, event_repo: EventRepository):
        # Внедряем зависимость (репозиторий)
        self.event_repo = event_repo
    
    async def execute(
        self,
        date_from: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """
        Выполнить бизнес-логику:
        1. Получить события из репозитория
        2. Посчитать общее количество
        3. Вернуть результат с метаданными пагинации
        """
        # Валидация входных данных
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:  # Ограничиваем размер страницы
            page_size = 100
        
        # Вычисляем offset для пагинации
        offset = (page - 1) * page_size
        
        # Получаем данные через репозиторий
        events = await self.event_repo.get_all(
            date_from=date_from,
            limit=page_size,
            offset=offset
        )
        
        total = await self.event_repo.count(date_from=date_from)
        
        # Вычисляем общее количество страниц
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "events": events,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
