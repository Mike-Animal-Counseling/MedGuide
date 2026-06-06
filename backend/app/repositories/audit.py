from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLog, session)

    async def list_for_target(self, target_user_id: UUID) -> list[AuditLog]:
        result = await self.session.scalars(
            select(AuditLog)
            .where(AuditLog.target_user_id == target_user_id)
            .order_by(AuditLog.created_at)
        )
        return list(result)
