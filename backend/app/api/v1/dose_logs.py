from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_dose_log_service
from app.models.schedule import DoseLog
from app.models.user import User
from app.schemas.schedule import DoseConfirmRequest, DoseLogResponse, DoseStatusRequest
from app.services.schedule import DoseLogService

router = APIRouter(prefix="/dose-logs", tags=["dose logs"])


@router.get("", response_model=list[DoseLogResponse])
async def list_dose_logs(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DoseLogService, Depends(get_dose_log_service)],
) -> list[DoseLog]:
    return await service.list_for_user(user)


@router.get("/today", response_model=list[DoseLogResponse])
async def list_todays_dose_logs(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DoseLogService, Depends(get_dose_log_service)],
) -> list[DoseLog]:
    return await service.today(user)


@router.patch("/{dose_log_id}/confirm", response_model=DoseLogResponse)
async def confirm_dose(
    dose_log_id: UUID,
    request: DoseConfirmRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DoseLogService, Depends(get_dose_log_service)],
) -> DoseLog:
    return await service.confirm(user, dose_log_id, request)


@router.patch("/{dose_log_id}/skip", response_model=DoseLogResponse)
async def skip_dose(
    dose_log_id: UUID,
    request: DoseStatusRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DoseLogService, Depends(get_dose_log_service)],
) -> DoseLog:
    return await service.skip(user, dose_log_id, request)


@router.patch("/{dose_log_id}/needs-help", response_model=DoseLogResponse)
async def mark_dose_needs_help(
    dose_log_id: UUID,
    request: DoseStatusRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DoseLogService, Depends(get_dose_log_service)],
) -> DoseLog:
    return await service.needs_help(user, dose_log_id, request)
