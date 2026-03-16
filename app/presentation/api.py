# FastAPI эндпоинты. Преобразуют HTTP запросы в вызовы use case и обратно.
# Получает HTTP запрос. Извлекает параметры (page, page_size). Вызывает GetEventsUseCase
# app/presentation/api.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import date
import logging
from urllib.parse import urlencode

from app.application.get_events import GetEventsUseCase
from app.infrastructure.event_repository import EventRepository
from app.presentation import schemas
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.sync_events import SyncEventsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["events"])


def get_events_usecase(
    session: AsyncSession = Depends(get_db)  # получаем сессию
) -> GetEventsUseCase:
    repo = EventRepository(session)  # передаем сессию в репозиторий
    return GetEventsUseCase(repo)


@router.get("/events", response_model=schemas.EventsListResponse)
async def get_events(
    # Query параметры из запроса
    date_from: Optional[date] = Query(None, description="События после даты"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    usecase: GetEventsUseCase = Depends(get_events_usecase),
):
    """
    Получить список событий с фильтрацией и пагинацией
    
    - **date_from**: фильтр по дате (YYYY-MM-DD)
    - **page**: номер страницы
    - **page_size**: размер страницы (макс 100)
    """
    
    # Вызываем бизнес-логику
    result = await usecase.execute(
        date_from=date_from,
        page=page,
        page_size=page_size
    )
    
    # Формируем ссылки для пагинации
    base_url = "/api/events"
    
    def build_url(p: int) -> Optional[str]:
        if p < 1 or p > result["total_pages"]:
            return None
        
        params = {}
        if date_from:
            params["date_from"] = str(date_from)
        params["page"] = p
        params["page_size"] = page_size
        
        return f"{base_url}?{urlencode(params)}"
    
    # Преобразуем доменные модели в Pydantic схемы для ответа
    events_data = []
    for event in result["events"]:
        events_data.append(schemas.EventResponse(
            id=event.id,
            name=event.name,
            place=schemas.PlaceResponse(
                id=event.place_id,
                name=event.place_name,
                city=event.place_city,
                address=event.place_address
            ),
            event_time=event.event_time,
            registration_deadline=event.registration_deadline,
            status=event.status.value,
            number_of_visitors=event.number_of_visitors
        ))
    
    return schemas.EventsListResponse(
        count=result["total"],
        next=build_url(result["page"] + 1),
        previous=build_url(result["page"] - 1),
        results=events_data
    )


@router.post("/sync/trigger", status_code=200)
async def trigger_sync(session: AsyncSession = Depends(get_db)):
    """
    Ручной запуск синхронизации с Events Provider API.
    
    Returns:
        {"message": "Synchronized X events"}
    """
    logger.info("Ручная проверка мероприятий")
    try:
        service = SyncEventsService(session)
        logger.info("Успешный запрос на сервис")
        count = await service.sync()
        return {"message": f"Synchronized {count} events"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
