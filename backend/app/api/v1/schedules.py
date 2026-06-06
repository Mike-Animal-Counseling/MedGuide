from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import get_current_user, get_schedule_service
from app.models.schedule import MedicationSchedule
from app.models.user import User
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from app.services.schedule import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    request: ScheduleCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> MedicationSchedule:
    return await service.create(user, request)


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    patient_id: Annotated[UUID | None, Query()] = None,
) -> list[MedicationSchedule]:
    return await service.list_for_user(user, patient_id)


@router.get("/today", response_model=list[ScheduleResponse])
async def list_todays_schedules(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    patient_id: Annotated[UUID | None, Query()] = None,
) -> list[MedicationSchedule]:
    return await service.today(user, patient_id=patient_id)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    request: ScheduleUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> MedicationSchedule:
    return await service.update(user, schedule_id, request)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> Response:
    await service.delete(user, schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
