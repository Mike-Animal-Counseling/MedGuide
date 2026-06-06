from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redaction import safe_audit_metadata
from app.models.audit import AuditLog
from app.repositories.audit import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession, request_id: str | None = None) -> None:
        self.session = session
        self.request_id = request_id
        self.logs = AuditLogRepository(session)

    async def record(
        self,
        *,
        action: str,
        resource_type: str,
        actor_user_id: UUID | None = None,
        target_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        return await self.logs.add(
            AuditLog(
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_=safe_audit_metadata(metadata),
                request_id=self.request_id,
            )
        )


class NullAuditService:
    async def record(self, **kwargs: object) -> None:
        return None
