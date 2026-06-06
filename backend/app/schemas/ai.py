from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai_verification import VerificationResult, VerificationType


class ScanLabelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: UUID


class ScanLabelResponse(BaseModel):
    result: Literal["LABEL_READ", "UNREADABLE_IMAGE"]
    ocr_text: str | None
    extracted_fields: dict[str, Any]
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    requires_confirmation: Literal[True] = True
    safety_message: str


class VerifyMedicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dose_log_id: UUID
    image_id: UUID
    verification_type: Literal[VerificationType.PILL_VERIFY, VerificationType.BOTTLE_VERIFY]


class VerifyMedicationResponse(BaseModel):
    result: VerificationResult
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    requires_confirmation: Literal[True] = True
    safety_message: str
