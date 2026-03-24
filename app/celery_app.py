# app/celery_app.py
from celery import Celery
from app.config import settings

# Формат для PostgreSQL брокера через SQLAlchemy
# sqla+postgresql://user:pass@host/db
broker_url = settings.SYNC_DATABASE_URL.replace("postgresql://", "sqla+postgresql://")
result_backend = settings.SYNC_DATABASE_URL
print(f"Broker URL: {broker_url}")
print(f"Backend URL: {result_backend}")

celery_app = Celery(
    "events_aggregator",
    broker=broker_url,
    backend=result_backend,
    include=["app.celery_tasks"]
)

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,
    # Настройки для PostgreSQL брокера
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 час
        "max_retries": 3,
    },
    # Периодические задачи
    beat_schedule={
        "sync-events-every-day": {
            "task": "app.celery_tasks.sync_events_task",
            "schedule": 24 * 60 * 60,  # раз в сутки
            "options": {
                "expires": 23 * 60 * 60,  # задача устаревает через 23 часа
            }
        },
    },
)
