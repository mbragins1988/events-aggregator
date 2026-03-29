from datetime import date
import logging
from typing import AsyncGenerator, Optional
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.cancel_ticket import CancelTicketUseCase
from app.application.create_ticket import CreateTicketUseCase
from app.application.get_events import GetEventsUseCase
from app.application.get_seats import GetSeatsUseCase
from app.application.sync_events import SyncEventsService
from app.config import settings
from app.database import get_db
from app.domain.exceptions import (
    EventAlreadyPassedError,
    EventNotFoundError,
    EventNotPublishedError,
    IdempotencyConflictError,
    RegistrationDeadlinePassedError,
    SeatNotAvailableError,
    TicketCreationError,
    TicketNotFoundError,
)
from app.infrastructure.event_repository import EventRepository
from app.infrastructure.events_provider_client import EventsProviderClient
from app.infrastructure.ticket_repository import TicketRepository
from app.presentation import schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["events"])


async def get_events_provider_client() -> AsyncGenerator[EventsProviderClient, None]:
    """Dependency для получения клиента Events Provider API"""
    client = EventsProviderClient(
        base_url=settings.CATALOG_BASE_URL, api_key=settings.API_TOKEN
    )
    try:
        yield client
    finally:
        await client.close()


def get_events_usecase(session: AsyncSession = Depends(get_db)) -> GetEventsUseCase:
    repo = EventRepository(session)
    return GetEventsUseCase(repo)


def get_event_repository(session: AsyncSession = Depends(get_db)) -> EventRepository:
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

    result = await usecase.execute(date_from=date_from, page=page, page_size=page_size)

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
        events_data.append(
            schemas.EventResponse(
                id=event.id,
                name=event.name,
                place=schemas.PlaceResponse(
                    id=event.place_id,
                    name=event.place_name,
                    city=event.place_city,
                    address=event.place_address,
                ),
                event_time=event.event_time,
                registration_deadline=event.registration_deadline,
                status=event.status.value,
                number_of_visitors=event.number_of_visitors,
            )
        )

    return schemas.EventsListResponse(
        count=result["total"],
        next=build_url(result["page"] + 1),
        previous=build_url(result["page"] - 1),
        results=events_data,
    )


@router.get("/events/{event_id}", response_model=schemas.EventDetailResponse)
async def get_event(
    event_id: str, repo: EventRepository = Depends(get_event_repository)
):
    """
    Получить детальную информацию о событии по ID

    - **event_id**: UUID события
    """
    event = await repo.get_by_id(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return schemas.EventDetailResponse(
        id=event.id,
        name=event.name,
        place=schemas.PlaceDetailResponse(
            id=event.place_id,
            name=event.place_name,
            city=event.place_city,
            address=event.place_address,
            seats_pattern=event.place_seats_pattern,
        ),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


@router.post("/sync/trigger", status_code=200)
async def trigger_sync(session: AsyncSession = Depends(get_db)):
    """
    Ручной запуск синхронизации.
    Выполняется синхронно, возвращает результат.
    """
    logger.info("Manual sync triggered")
    service = SyncEventsService(session)
    count = await service.sync()
    return {"message": f"Synchronized {count} events"}


@router.get("/sync/status/{task_id}")
async def get_sync_status(task_id: str):
    """
    Получить статус задачи синхронизации.
    """
    from app.celery_app import celery_app

    task = celery_app.AsyncResult(task_id)

    if task.pending:
        status = "pending"
    elif task.failed():
        status = "failed"
        result = str(task.info) if task.info else "Unknown error"
    elif task.successful():
        status = "success"
        result = task.result
    else:
        status = "unknown"
        result = None

    return {"task_id": task_id, "status": status, "result": result}


@router.get("/events/{event_id}/seats", response_model=schemas.SeatsResponse)
async def get_event_seats(
    event_id: str,
    session: AsyncSession = Depends(get_db),
    api_client: EventsProviderClient = Depends(
        get_events_provider_client
    ),  # ← добавили
):
    event_repo = EventRepository(session)

    usecase = GetSeatsUseCase(event_repo=event_repo, api_client=api_client)

    try:
        seats = await usecase.execute(event_id)
        return schemas.SeatsResponse(event_id=event_id, available_seats=seats)
    except EventNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Event with id {event_id} not found"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_event_seats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tickets", response_model=schemas.TicketResponse, status_code=201)
async def create_ticket(
    request: schemas.TicketCreateRequest, session: AsyncSession = Depends(get_db)
):
    logger.info(f"Creating ticket for event {request.event_id}, seat {request.seat}")

    # Валидация UUID
    try:
        UUID(request.event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    event_repo = EventRepository(session)
    ticket_repo = TicketRepository(session)
    api_client = EventsProviderClient(
        base_url=settings.CATALOG_BASE_URL, api_key=settings.API_TOKEN
    )

    usecase = CreateTicketUseCase(
        event_repo=event_repo,
        ticket_repo=ticket_repo,
        api_client=api_client,
        session=session,
    )

    try:
        ticket_id = await usecase.execute(
            event_id=request.event_id,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            seat=request.seat,
            idempotency_key=request.idempotency_key,  # ← передаем ключ
        )

        return schemas.TicketResponse(ticket_id=ticket_id)

    except EventNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))  # ← 409 Conflict
    except (
        EventNotPublishedError,
        RegistrationDeadlinePassedError,
        SeatNotAvailableError,
        TicketCreationError,
    ) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await api_client.close()


@router.delete("/tickets/{ticket_id}", response_model=schemas.CancelResponse)
async def cancel_ticket(
    ticket_id: str,
    session: AsyncSession = Depends(get_db),
    api_client: EventsProviderClient = Depends(
        get_events_provider_client
    ),  # ← добавили
):
    ticket_repo = TicketRepository(session)
    event_repo = EventRepository(session)

    usecase = CancelTicketUseCase(
        ticket_repo=ticket_repo, event_repo=event_repo, api_client=api_client
    )

    try:
        success = await usecase.execute(ticket_id)

        logger.info(f"Ticket {ticket_id} cancelled successfully")

        return {"success": success}

    except TicketNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (EventNotFoundError, EventAlreadyPassedError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in cancel_ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
