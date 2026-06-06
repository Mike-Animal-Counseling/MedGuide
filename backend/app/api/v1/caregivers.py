from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_caregiver_service, get_current_user
from app.models.caregiver import CaregiverLink
from app.models.schedule import DoseLog
from app.models.user import User
from app.schemas.caregiver import (
    CaregiverAcceptRequest,
    CaregiverInviteRequest,
    CaregiverInviteResponse,
    CaregiverLinkResponse,
    LinkedPatientResponse,
    PatientTodayResponse,
)
from app.schemas.schedule import DoseLogResponse
from app.services.caregiver import CaregiverService

router = APIRouter(prefix="/caregivers", tags=["caregivers"])


@router.post("/invite", response_model=CaregiverInviteResponse, status_code=201)
async def invite_caregiver(
    request: CaregiverInviteRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CaregiverService, Depends(get_caregiver_service)],
) -> CaregiverInviteResponse:
    link, invite_token = await service.invite(user, request)
    response = CaregiverInviteResponse.model_validate(link)
    return response.model_copy(update={"invite_token": invite_token})


@router.post("/accept", response_model=CaregiverLinkResponse)
async def accept_caregiver_invite(
    request: CaregiverAcceptRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CaregiverService, Depends(get_caregiver_service)],
) -> CaregiverLink:
    return await service.accept(user, request)


@router.get("/patients", response_model=list[LinkedPatientResponse])
async def list_linked_patients(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CaregiverService, Depends(get_caregiver_service)],
) -> list[LinkedPatientResponse]:
    return await service.list_patients(user)


@router.get("/patients/{patient_id}/today", response_model=PatientTodayResponse)
async def get_linked_patient_today(
    patient_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CaregiverService, Depends(get_caregiver_service)],
) -> PatientTodayResponse:
    return await service.today(user, patient_id)


@router.get("/patients/{patient_id}/dose-logs", response_model=list[DoseLogResponse])
async def get_linked_patient_dose_logs(
    patient_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CaregiverService, Depends(get_caregiver_service)],
) -> list[DoseLog]:
    return await service.dose_logs(user, patient_id)


@router.patch("/links/{link_id}/revoke", response_model=CaregiverLinkResponse)
async def revoke_caregiver_link(
    link_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CaregiverService, Depends(get_caregiver_service)],
) -> CaregiverLink:
    return await service.revoke(user, link_id)
