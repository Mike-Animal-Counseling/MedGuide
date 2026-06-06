from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Numeric, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VerificationType(StrEnum):
    LABEL_OCR = "LABEL_OCR"
    PILL_VERIFY = "PILL_VERIFY"
    BOTTLE_VERIFY = "BOTTLE_VERIFY"


class VerificationResult(StrEnum):
    MATCH_LIKELY = "MATCH_LIKELY"
    MATCH_UNCERTAIN = "MATCH_UNCERTAIN"
    NO_MATCH = "NO_MATCH"
    UNREADABLE_IMAGE = "UNREADABLE_IMAGE"
    CAREGIVER_REVIEW_REQUIRED = "CAREGIVER_REVIEW_REQUIRED"


class AIVerificationEvent(Base):
    __tablename__ = "ai_verification_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    medication_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("medications.id"), index=True, default=None
    )
    dose_log_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dose_logs.id"), index=True, default=None
    )
    image_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("uploaded_images.id"), index=True, default=None
    )
    verification_type: Mapped[VerificationType] = mapped_column(
        Enum(VerificationType, name="verification_type")
    )
    ocr_text: Mapped[str | None] = mapped_column(Text, default=None)
    extracted_fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=None
    )
    visual_features: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=None
    )
    model_output: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=None
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), default=None)
    result: Mapped[VerificationResult] = mapped_column(
        Enum(VerificationResult, name="verification_result")
    )
    safety_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
