from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlaceResponse(BaseModel):
    """Ответ с данными площадки"""

    id: UUID
    name: str
    city: str
    address: str


class PlaceDetailResponse(PlaceResponse):
    """Детальный ответ с данными площадки (включает схему мест)"""

    seats_pattern: str


class EventResponse(BaseModel):
    """Ответ с данными события"""

    id: UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventDetailResponse(BaseModel):
    """Детальный ответ с данными события (для GET /events/{id})"""

    id: UUID
    name: str
    place: PlaceDetailResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventsListResponse(BaseModel):
    """Ответ со списком событий (с пагинацией)"""

    count: int
    next: str | None
    previous: str | None
    results: list[EventResponse]


class SeatsResponse(BaseModel):
    """Ответ со списком свободных мест"""

    event_id: str
    available_seats: list[str]


class TicketResponse(BaseModel):
    """Ответ с созданным билетом"""

    ticket_id: str


class CancelResponse(BaseModel):
    """Ответ на отмену регистрации"""

    success: bool


class TicketCreateRequest(BaseModel):
    """Запрос на создание билета (регистрацию)"""

    event_id: str
    first_name: str
    last_name: str
    email: str
    seat: str
    idempotency_key: str | None = None
