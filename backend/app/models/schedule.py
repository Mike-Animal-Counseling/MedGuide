from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FrequencyType(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    EVERY_X_HOURS = "EVERY_X_HOURS"
    AS_NEEDED = "AS_NEEDED"


class DoseStatus(StrEnum):
    PENDING = "PENDING"
    TAKEN_ON_TIME = "TAKEN_ON_TIME"
    TAKEN_LATE = "TAKEN_LATE"
    SKIPPED = "SKIPPED"
    MISSED = "MISSED"
    NEEDS_HELP = "NEEDS_HELP"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class ConfirmationMethod(StrEnum):
    VOICE = "VOICE"
    BUTTON = "BUTTON"
    CAREGIVER = "CAREGIVER"
    AUTO_MISSED = "AUTO_MISSED"


class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_medication_schedules_date_range",
        ),
        CheckConstraint(
            "frequency_type != 'EVERY_X_HOURS' OR interval_hours > 0",
            name="ck_medication_schedules_interval_hours",
        ),
        Index("ix_medication_schedules_user_active", "user_id", "active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    medication_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("medications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    frequency_type: Mapped[FrequencyType] = mapped_column(
        Enum(FrequencyType, name="frequency_type")
    )
    scheduled_time: Mapped[time | None] = mapped_column(Time, default=None)
    days_of_week: Mapped[list[str] | None] = mapped_column(
        JSON().with_variant(ARRAY(String(3)), "postgresql"), default=None
    )
    interval_hours: Mapped[int | None] = mapped_column(Integer, default=None)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    reminder_offset_minutes: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    medication = relationship("Medication")
    creator = relationship("User", foreign_keys=[created_by])


class DoseLog(Base):
    __tablename__ = "dose_logs"
    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_time", name="uq_dose_logs_schedule_time"),
        Index("ix_dose_logs_user_scheduled_time", "user_id", "scheduled_time"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    medication_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("medications.id"), index=True)
    schedule_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("medication_schedules.id"), index=True
    )
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_taken_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    status: Mapped[DoseStatus] = mapped_column(
        Enum(DoseStatus, name="dose_status"), default=DoseStatus.PENDING
    )
    confirmation_method: Mapped[ConfirmationMethod | None] = mapped_column(
        Enum(ConfirmationMethod, name="confirmation_method"), default=None
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    schedule = relationship("MedicationSchedule")
    medication = relationship("Medication")
