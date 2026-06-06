from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MedicationForm(StrEnum):
    TABLET = "TABLET"
    CAPSULE = "CAPSULE"
    LIQUID = "LIQUID"
    INJECTION = "INJECTION"
    OTHER = "OTHER"


class MedicationSource(StrEnum):
    MANUAL = "MANUAL"
    OCR = "OCR"
    CAREGIVER = "CAREGIVER"


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (
        CheckConstraint(
            "source != 'OCR' OR active = false OR confirmed_by IS NOT NULL",
            name="ck_medications_ocr_active_requires_confirmation",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_medications_name_not_blank",
        ),
        CheckConstraint(
            "source != 'OCR' OR instructions IS NULL OR confirmed_by IS NOT NULL",
            name="ck_medications_ocr_instructions_require_confirmation",
        ),
        Index("ix_medications_user_active", "user_id", "active", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(300))
    generic_name: Mapped[str | None] = mapped_column(String(300), default=None)
    brand_name: Mapped[str | None] = mapped_column(String(300), default=None)
    dosage: Mapped[str | None] = mapped_column(String(200), default=None)
    form: Mapped[MedicationForm] = mapped_column(Enum(MedicationForm, name="medication_form"))
    instructions: Mapped[str | None] = mapped_column(Text, default=None)
    with_food: Mapped[bool | None] = mapped_column(Boolean, default=None)
    pill_color: Mapped[str | None] = mapped_column(String(100), default=None)
    pill_shape: Mapped[str | None] = mapped_column(String(100), default=None)
    imprint: Mapped[str | None] = mapped_column(String(100), default=None)
    label_image_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("uploaded_images.id", ondelete="SET NULL"), index=True, default=None
    )
    pill_image_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("uploaded_images.id", ondelete="SET NULL"), index=True, default=None
    )
    source: Mapped[MedicationSource] = mapped_column(
        Enum(MedicationSource, name="medication_source"), default=MedicationSource.MANUAL
    )
    confirmed_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    owner = relationship("User", foreign_keys=[user_id])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    label_image = relationship("UploadedImage", foreign_keys=[label_image_id])
    pill_image = relationship("UploadedImage", foreign_keys=[pill_image_id])
