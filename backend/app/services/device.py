from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.notification import UserDevice
from app.models.user import User
from app.repositories.notification import UserDeviceRepository
from app.schemas.notification import DeviceCreateRequest


class DeviceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.devices = UserDeviceRepository(session)

    async def register(self, user: User, request: DeviceCreateRequest) -> UserDevice:
        device = await self.devices.get_by_token(request.push_token)
        if device is None:
            device = await self.devices.add(
                UserDevice(
                    user_id=user.id,
                    platform=request.platform,
                    push_token=request.push_token,
                )
            )
        else:
            device.user_id = user.id
            device.platform = request.platform
            device.active = True
            device.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def delete(self, user: User, device_id: UUID) -> None:
        device = await self.devices.get_for_user(device_id, user.id)
        if device is None:
            raise AppError(code="device_not_found", message="Device not found", status_code=404)
        device.active = False
        await self.session.commit()
