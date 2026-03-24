from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Асинхронный движок для приложения
async_engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(
    async_engine,  # Движок, который будет использовать
    class_=AsyncSession,  # Тип сессии (асинхронная)
    # Важно: после commit() объекты остаются доступными для чтения.
    # Без параметра expire_on_commit после вызова session.commit() все загруженные объекты "истекают"
    # и при попытке обратиться к их атрибутам SQLAlchemy сделает новый запрос к БД.
    # После commit() мы часто возвращаем объект клиенту (через Pydantic),
    # и нам не нужно, чтобы SQLAlchemy делала дополнительные запросы.
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
