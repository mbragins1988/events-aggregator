# app/domain/models.py
from datetime import datetime
from uuid import UUID
from enum import Enum
from typing import Optional


class EventStatus(str, Enum):
    NEW = "new"
    PUBLISHED = "published"


class Event:
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
        changed_at: datetime,
        created_at: datetime,
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
        self.changed_at = changed_at
        self.created_at = created_at

    def can_register(self, current_time: datetime) -> bool:
        return (
            self.status == EventStatus.PUBLISHED and
            current_time <= self.registration_deadline
        )

    def in_city(self, city: str) -> bool:
        return self.place_city.lower() == city.lower()


class Ticket:
    def __init__(
        self,
        id: UUID,
        event_id: UUID,
        seat: str,
        first_name: str,
        last_name: str,
        email: str,
        registered_at: datetime,
    ):
        self.id = id
        self.event_id = event_id
        self.seat = seat
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.registered_at = registered_at


class SyncMetadata:
    def __init__(
        self,
        last_changed_at: Optional[datetime] = None,
        last_sync_date: Optional[datetime] = None,
    ):
        self.last_changed_at = last_changed_at
        self.last_sync_date = last_sync_date

    def get_changed_at_param(self) -> str:
        if not self.last_changed_at:
            return "2000-01-01"
        return self.last_changed_at.date().isoformat()

    def should_sync(self, current_time: datetime) -> bool:
        if not self.last_sync_date:
            return True
        return (current_time - self.last_sync_date).total_seconds() > 24 * 60 * 60
