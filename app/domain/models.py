# Чистые Python классы с бизнес-логикой. Не знают про БД и фреймворки.
from datetime import datetime
from uuid import UUID
from enum import Enum
from pydantic import BaseModel


class EventStatus(str, Enum):
    """Статус события из ТЗ"""
    NEW = "new"
    PUBLISHED = "published"


class Event(BaseModel):
    """Событие - чистая доменная модель"""

    def __init__(
        self,
        id: UUID,
        name: str,
        place_id: UUID,
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
        """Бизнес-правило: опубликовано ли событие"""
        return self.status == EventStatus.PUBLISHED
    
    def in_city(self, city: str) -> bool:
        """Бизнес-правило: проверка города"""
        return self.place_city.lower() == city.lower()
