# app/domain/models.py
from datetime import datetime
from enum import Enum
from typing import Optional


class EventStatus(str, Enum):
    NEW = "new"
    PUBLISHED = "published"
    REGISTRATION_CLOSED = "registration_closed"
    FINISHED = "finished"
    
    @classmethod
    def _missing_(cls, value):
        # Любой неизвестный статус логируем, но не падаем
        print(f"Warning: Unknown event status '{value}'")
        return None


class Event:
    def __init__(
        self,
        id: str,
        name: str,
        place_id: str,
        place_name: str,
        place_city: str,
        place_address: str,
        place_seats_pattern: str,
        event_time: datetime,
        registration_deadline: datetime,
        status: EventStatus,
        number_of_visitors: int,
        created_at: datetime,
        status_changed_at: datetime,
    ):
        self.id = id
        self.name = name
        self.place_id = place_id
        self.place_name = place_name
        self.place_city = place_city
        self.place_address = place_address
        self.place_seats_pattern = place_seats_pattern
        self.event_time = event_time
        self.registration_deadline = registration_deadline
        self.status = status
        self.number_of_visitors = number_of_visitors
        self.created_at = created_at
        self.status_changed_at = status_changed_at

    def is_published(self) -> bool:
        return self.status == EventStatus.PUBLISHED

    def can_register(self, current_time: datetime) -> bool:
        return (
            self.status == EventStatus.PUBLISHED and
            current_time <= self.registration_deadline
        )

    def is_published(self) -> bool:
        """Проверка, опубликовано ли событие"""
        return self.status == "published"

    def in_city(self, city: str) -> bool:
        return self.place_city.lower() == city.lower()


class Ticket:
    """
    Доменная модель билета (регистрации).
    
    Хранит информацию о регистрации участника на событие.
    Используется для связи ticket_id (из внешнего API) с event_id.
    """
    
    def __init__(
        self,
        id: str,              # ticket_id из внешнего API
        event_id: str,         # ID события
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.event_id = event_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.seat = seat
        self.created_at = created_at or datetime.now()
    
    @property
    def full_name(self) -> str:
        """Полное имя участника"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def belongs_to_event(self, event_id: str) -> bool:
        """Проверка, относится ли билет к указанному событию"""
        return self.event_id == event_id
    
    def matches_email(self, email: str) -> bool:
        """Проверка email участника"""
        return self.email.lower() == email.lower()
