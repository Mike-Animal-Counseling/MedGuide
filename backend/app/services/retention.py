from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.repositories.upload import UploadedImageRepository
from app.services.audit import AuditService
from app.services.storage import StorageProvider


class RetentionCleanupService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        storage: StorageProvider,
        audit: AuditService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.images = UploadedImageRepository(session)
        self.audit = audit or AuditService(session)

    async def cleanup_expired_images(self, now: datetime | None = None) -> int:
        if self.settings.storage_retention_days is None:
            return 0
        cutoff = (now or datetime.now(UTC)) - timedelta(days=self.settings.storage_retention_days)
        deleted = 0
        for image in await self.images.list_active_created_before(cutoff):
            if image.provider != self.storage.name:
                continue
            await self.storage.delete_object(object_key=image.object_key)
            await self.images.soft_delete(image)
            await self.audit.record(
                action="image.deleted",
                actor_user_id=None,
                target_user_id=image.user_id,
                resource_type="uploaded_image",
                resource_id=image.id,
                metadata={"retention_cleanup": True},
            )
            deleted += 1
        await self.session.commit()
        return deleted
