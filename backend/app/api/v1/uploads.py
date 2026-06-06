from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_current_user, get_upload_service
from app.models.user import User
from app.schemas.upload import SignedReadResponse, SignedUploadRequest, SignedUploadResponse
from app.services.upload import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post(
    "/signed-url", response_model=SignedUploadResponse, status_code=status.HTTP_201_CREATED
)
async def create_signed_upload_url(
    request: SignedUploadRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> SignedUploadResponse:
    return await service.create_signed_upload(user, request)


@router.get("/{image_id}/signed-read-url", response_model=SignedReadResponse)
async def create_signed_read_url(
    image_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> SignedReadResponse:
    return await service.create_signed_read(user, image_id)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_uploaded_image(
    image_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> Response:
    await service.delete(user, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
