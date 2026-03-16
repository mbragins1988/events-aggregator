# app/presentation/schemas.py
# Схемы для валидации и сериализации API запросов/ответов.
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, List


class PlaceResponse(BaseModel):
    """Ответ с данными площадки"""
    id: UUID
    name: str
    city: str
    address: str


class EventResponse(BaseModel):
    """Ответ с данными события"""
    id: UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventsListResponse(BaseModel):
    """Ответ со списком событий (с пагинацией)"""
    count: int
    next: Optional[str]  # URL следующей страницы
    previous: Optional[str]  # URL предыдущей страницы
    results: List[EventResponse]
