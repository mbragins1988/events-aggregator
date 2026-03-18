# app/domain/models.py
from datetime import datetime
from enum import Enum
from typing import Optional


class EventStatus(str, Enum):
    NEW = "new"
    PUBLISHED = "published"
    REGISTRATION_CLOSED = "registration_closed"
    FINISHED = "finished"


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

    def in_city(self, city: str) -> bool:
        return self.place_city.lower() == city.lower()