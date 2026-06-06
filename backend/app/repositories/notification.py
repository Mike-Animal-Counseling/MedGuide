from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
    NotificationType,
    UserDevice,
)
from app.repositories.base import BaseRepository


class UserDeviceRepository(BaseRepository[UserDevice]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserDevice, session)

    async def get_by_token(self, push_token: str) -> UserDevice | None:
        return cast(
            UserDevice | None,
            await self.session.scalar(
                select(UserDevice).where(UserDevice.push_token == push_token)
            ),
        )

    async def get_for_user(self, device_id: UUID, user_id: UUID) -> UserDevice | None:
        return cast(
            UserDevice | None,
            await self.session.scalar(
                select(UserDevice).where(UserDevice.id == device_id, UserDevice.user_id == user_id)
            ),
        )

    async def list_active_tokens(self, user_id: UUID) -> list[str]:
        result = await self.session.scalars(
            select(UserDevice.push_token).where(
                UserDevice.user_id == user_id,
                UserDevice.active.is_(True),
            )
        )
        return list(result)


class NotificationEventRepository(BaseRepository[NotificationEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationEvent, session)

    async def get_for_delivery(
        self,
        *,
        dose_log_id: UUID,
        notification_type: NotificationType,
        channel: NotificationChannel,
        caregiver_id: UUID | None,
    ) -> NotificationEvent | None:
        query = select(NotificationEvent).where(
            NotificationEvent.dose_log_id == dose_log_id,
            NotificationEvent.notification_type == notification_type,
            NotificationEvent.channel == channel,
        )
        query = (
            query.where(NotificationEvent.caregiver_id.is_(None))
            if caregiver_id is None
            else query.where(NotificationEvent.caregiver_id == caregiver_id)
        )
        return cast(NotificationEvent | None, await self.session.scalar(query))

    async def list_for_dose(self, dose_log_id: UUID) -> list[NotificationEvent]:
        result = await self.session.scalars(
            select(NotificationEvent)
            .where(NotificationEvent.dose_log_id == dose_log_id)
            .order_by(NotificationEvent.created_at)
        )
        return list(result)

    async def list_failed_for_types(
        self, notification_types: set[NotificationType]
    ) -> list[NotificationEvent]:
        result = await self.session.scalars(
            select(NotificationEvent)
            .where(
                NotificationEvent.status == NotificationStatus.FAILED,
                NotificationEvent.notification_type.in_(notification_types),
                NotificationEvent.dose_log_id.is_not(None),
            )
            .order_by(NotificationEvent.created_at)
        )
        return list(result)
