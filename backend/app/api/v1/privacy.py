from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_current_user, get_privacy_service
from app.models.user import User
from app.schemas.privacy import PrivacyExportResponse
from app.services.privacy import PrivacyService

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/export", response_model=PrivacyExportResponse)
async def export_privacy_data(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PrivacyService, Depends(get_privacy_service)],
) -> dict[str, Any]:
    return await service.export(user)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_privacy_image(
    image_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PrivacyService, Depends(get_privacy_service)],
) -> Response:
    await service.delete_image(user, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/revoke-caregiver/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_caregiver_access(
    link_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PrivacyService, Depends(get_privacy_service)],
) -> Response:
    await service.revoke_caregiver(user, link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
