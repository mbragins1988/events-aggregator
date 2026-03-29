import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Capashino (Notification Service)
    CAPASHINO_BASE_URL: str = os.getenv("CAPASHINO_BASE_URL", "")

    # Outbox настройки
    OUTBOX_INTERVAL_SECONDS: int = int(os.getenv("OUTBOX_INTERVAL_SECONDS", "10"))

    # Database/
    POSTGRES_CONNECTION_STRING: str = os.getenv("POSTGRES_CONNECTION_STRING", "")

    # API
    API_TOKEN: str = os.getenv("API_TOKEN", "")

    # SENTRY_DSN
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    # Services
    CATALOG_BASE_URL: str = os.getenv("CATALOG_BASE_URL", "")

    @property
    def DATABASE_URL(self) -> str:
        """Асинхронный URL для приложения"""
        return self.POSTGRES_CONNECTION_STRING.replace(
            "postgres://", "postgresql+asyncpg://"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Синхронный URL для Alembic"""
        return self.POSTGRES_CONNECTION_STRING.replace("postgres://", "postgresql://")


settings = Settings()
