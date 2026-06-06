from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import get_current_user, get_medication_service
from app.models.medication import Medication
from app.models.user import User
from app.schemas.medication import (
    MedicationCreateRequest,
    MedicationResponse,
    MedicationUpdateRequest,
)
from app.services.medication import MedicationService

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("", response_model=list[MedicationResponse])
async def list_medications(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
    patient_id: Annotated[UUID | None, Query()] = None,
) -> list[Medication]:
    return await service.list_for_user(user, patient_id)


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    request: MedicationCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
    patient_id: Annotated[UUID | None, Query()] = None,
) -> Medication:
    return await service.create(user, request, patient_id)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
) -> Medication:
    return await service.get(user, medication_id)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: UUID,
    request: MedicationUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
) -> Medication:
    return await service.update(user, medication_id, request)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
) -> Response:
    await service.delete(user, medication_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
