# app/infrastructure/models.py
# Описание таблиц в БД. Alembic будет использовать это для создания таблиц
from sqlalchemy import Table, Column, String, Integer, DateTime, MetaData
from sqlalchemy.sql import func

# Метаданные - нужны для Alembic
metadata = MetaData()

# Таблица событий
events_tbl = Table(
    "events",
    metadata,
    Column("id", String, primary_key=True),  # UUID как строка
    Column("name", String, nullable=False),
    Column("place_id", String, nullable=False),
    Column("place_name", String, nullable=False),
    Column("place_city", String, nullable=False),
    Column("place_address", String, nullable=False),
    Column("place_seats_pattern", String, nullable=False),
    Column("event_time", DateTime(timezone=True), nullable=False),
    Column("registration_deadline", DateTime(timezone=True), nullable=False),
    Column("status", String, nullable=False),  # new/published
    Column("number_of_visitors", Integer, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("status_changed_at", DateTime(timezone=True),
           server_default=func.now(), onupdate=func.now()),
)


tickets_tbl = Table(
    "tickets",
    metadata,
    Column("id", String, primary_key=True),  # ticket_id из API
    Column("event_id", String, nullable=False),
    Column("first_name", String, nullable=False),
    Column("last_name", String, nullable=False),
    Column("email", String, nullable=False),
    Column("seat", String, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
