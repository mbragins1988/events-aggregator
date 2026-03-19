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

from app.infrastructure.events_provider_client import EventsProviderClient
from app.application.get_seats import GetSeatsUseCase
from app.domain.exceptions import EventNotFoundError
from app.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["events"])


def get_events_usecase(
    session: AsyncSession = Depends(get_db)
) -> GetEventsUseCase:
    repo = EventRepository(session)
    return GetEventsUseCase(repo)


def get_event_repository(
    session: AsyncSession = Depends(get_db)
) -> EventRepository:
    return EventRepository(session)


@router.get("/events", response_model=schemas.EventsListResponse)
async def get_events(
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
    
    result = await usecase.execute(
        date_from=date_from,
        page=page,
        page_size=page_size
    )
    
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


@router.get("/events/{event_id}", response_model=schemas.EventDetailResponse)
async def get_event(
    event_id: str,
    repo: EventRepository = Depends(get_event_repository)
):
    event = await repo.get_by_id(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Конвертируем Domain model в Pydantic schema для ответа
    return schemas.EventDetailResponse(
        id=event.id,
        name=event.name,
        place=schemas.PlaceDetailResponse(
            id=event.place_id,
            name=event.place_name,
            city=event.place_city,
            address=event.place_address,
            seats_pattern=event.place_seats_pattern
        ),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status.value,
        number_of_visitors=event.number_of_visitors
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


@router.get("/events/{event_id}/seats", response_model=schemas.SeatsResponse)
async def get_event_seats(
    event_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Получить список свободных мест на событии.
    
    Результат кэшируется на 30 секунд.
    
    - **event_id**: UUID события
    """
    # Создаем зависимости для use case
    event_repo = EventRepository(session)
    api_client = EventsProviderClient(
        base_url=settings.CATALOG_BASE_URL,
        api_key=settings.API_TOKEN
    )
    
    # Создаем и вызываем use case
    usecase = GetSeatsUseCase(
        event_repo=event_repo,
        api_client=api_client
    )
    
    try:
        seats = await usecase.execute(event_id)
        
        return schemas.SeatsResponse(
            event_id=event_id,
            available_seats=seats
        )
        
    except EventNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Event with id {event_id} not found"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_event_seats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
