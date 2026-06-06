from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_current_user, get_device_service
from app.models.notification import UserDevice
from app.models.user import User
from app.schemas.notification import DeviceCreateRequest, DeviceResponse
from app.services.device import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    request: DeviceCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> UserDevice:
    return await service.register(user, request)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> Response:
    await service.delete(user, device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
