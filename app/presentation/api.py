# app/presentation/api.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import date
import logging
from urllib.parse import urlencode

from app.application.get_events import GetEventsUseCase
from app.infrastructure.event_repository import EventRepository
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.sync_events import SyncEventsService

from app.infrastructure.events_provider_client import EventsProviderClient
from app.application.get_seats import GetSeatsUseCase
from app.config import settings

from app.application.create_ticket import CreateTicketUseCase
from app.domain.exceptions import (
    EventNotFoundError,
    EventNotPublishedError,
    RegistrationDeadlinePassedError,
    SeatNotAvailableError,
    TicketCreationError
)
from app.presentation import schemas


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
    logger.info(f"Getting event details for id: {event_id}")
    
    try:
        event = await repo.get_by_id(event_id)
        
        if not event:
            logger.warning(f"Event not found: {event_id}")
            raise HTTPException(status_code=404, detail="Event not found")
        
        logger.info(f"Event found: {event.id} - {event.name} - status: {event.status}")
        
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
            status=event.status,
            number_of_visitors=event.number_of_visitors
        )
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


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


@router.post("/tickets", response_model=schemas.TicketResponse, status_code=201)
async def create_ticket(
    request: schemas.TicketCreateRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Зарегистрироваться на событие.
    
    - **event_id**: UUID события
    - **first_name**: Имя участника
    - **last_name**: Фамилия участника
    - **email**: Email участника
    - **seat**: Желаемое место (например, "A15")
    
    Returns:
        ticket_id: UUID созданного билета
    """
    logger.info(f"Creating ticket for event {request.event_id}, seat {request.seat}")
    
    # Создаем зависимости
    event_repo = EventRepository(session)
    api_client = EventsProviderClient(
        base_url=settings.CATALOG_BASE_URL,
        api_key=settings.API_TOKEN
    )
    
    # Создаем use case
    usecase = CreateTicketUseCase(
        event_repo=event_repo,
        api_client=api_client
    )
    
    try:
        ticket_id = await usecase.execute(
            event_id=request.event_id,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            seat=request.seat
        )
        
        logger.info(f"Ticket created successfully: {ticket_id}")
        
        return schemas.TicketResponse(ticket_id=ticket_id)
        
    except EventNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EventNotPublishedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RegistrationDeadlinePassedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SeatNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TicketCreationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
