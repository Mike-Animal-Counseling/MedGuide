from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import (
    get_current_user,
    get_label_scan_service,
    get_medication_verification_service,
)
from app.models.user import User
from app.schemas.ai import (
    ScanLabelRequest,
    ScanLabelResponse,
    VerifyMedicationRequest,
    VerifyMedicationResponse,
)
from app.services.label_scan import LabelScanService
from app.services.medication_verification import MedicationVerificationService

router = APIRouter(prefix="/ai", tags=["AI assistance"])


@router.post("/scan-label", response_model=ScanLabelResponse)
async def scan_medication_label(
    request: ScanLabelRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[LabelScanService, Depends(get_label_scan_service)],
) -> ScanLabelResponse:
    return await service.scan_label(user, request.image_id)


@router.post("/verify-medication", response_model=VerifyMedicationResponse)
async def verify_medication(
    request: VerifyMedicationRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MedicationVerificationService, Depends(get_medication_verification_service)],
) -> VerifyMedicationResponse:
    return await service.verify(user, **request.model_dump())
