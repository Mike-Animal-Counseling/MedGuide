from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import UploadedImage
from app.repositories.base import BaseRepository


class UploadedImageRepository(BaseRepository[UploadedImage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UploadedImage, session)

    async def get_active(self, image_id: UUID) -> UploadedImage | None:
        return cast(
            UploadedImage | None,
            await self.session.scalar(
                select(UploadedImage).where(
                    UploadedImage.id == image_id,
                    UploadedImage.deleted_at.is_(None),
                )
            ),
        )

    async def soft_delete(self, image: UploadedImage) -> None:
        image.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def list_active_created_before(self, cutoff: datetime) -> list[UploadedImage]:
        result = await self.session.scalars(
            select(UploadedImage).where(
                UploadedImage.created_at < cutoff,
                UploadedImage.deleted_at.is_(None),
            )
        )
        return list(result)
