from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_current_user, get_user_service
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await service.update_current_user(user, request)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> Response:
    await service.delete_current_user(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
