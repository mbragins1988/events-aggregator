# app/infrastructure/sync_metadata_repository.py
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db_schema import sync_metadata_tbl
from app.domain.models import SyncMetadata


class SyncMetadataRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> SyncMetadata:
        """Получить метаданные синхронизации (всегда одна запись)"""
        query = select(sync_metadata_tbl).where(sync_metadata_tbl.c.id == "singleton")
        result = await self.session.execute(query)
        row = result.first()

        if not row:
            # Если записи нет, создаем новую
            metadata = SyncMetadata()
            await self._save(metadata)
            return metadata

        return SyncMetadata(
            id=row.id,
            last_changed_at=row.last_changed_at,
            last_sync_time=row.last_sync_time,
            total_events_synced=row.total_events_synced,
            last_sync_status=row.last_sync_status,
            last_error=row.last_error,
        )

    async def _save(self, metadata: SyncMetadata):
        """Сохранить метаданные"""
        stmt = sync_metadata_tbl.insert().values(
            id=metadata.id,
            last_changed_at=metadata.last_changed_at,
            last_sync_time=metadata.last_sync_time,
            total_events_synced=metadata.total_events_synced,
            last_sync_status=metadata.last_sync_status,
            last_error=metadata.last_error,
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update(self, metadata: SyncMetadata):
        """Обновить метаданные"""
        stmt = (
            update(sync_metadata_tbl)
            .where(sync_metadata_tbl.c.id == metadata.id)
            .values(
                last_changed_at=metadata.last_changed_at,
                last_sync_time=metadata.last_sync_time,
                total_events_synced=metadata.total_events_synced,
                last_sync_status=metadata.last_sync_status,
                last_error=metadata.last_error,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
