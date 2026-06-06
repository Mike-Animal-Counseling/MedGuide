from datetime import UTC, date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.schedule import ConfirmationMethod, DoseStatus, FrequencyType

DayOfWeek = Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


class ScheduleFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medication_id: UUID
    frequency_type: FrequencyType
    scheduled_time: time | None = None
    days_of_week: list[DayOfWeek] | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=168)
    start_date: date
    end_date: date | None = None
    reminder_offset_minutes: int = Field(default=0, ge=0, le=10080)
    active: bool = True

    @field_validator("days_of_week")
    @classmethod
    def normalize_days(cls, value: list[DayOfWeek] | None) -> list[DayOfWeek] | None:
        return sorted(set(value)) if value else value

    @model_validator(mode="after")
    def validate_frequency_fields(self) -> "ScheduleFields":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.frequency_type in {FrequencyType.DAILY, FrequencyType.WEEKLY}:
            if self.scheduled_time is None:
                raise ValueError("scheduled_time is required for DAILY and WEEKLY schedules")
        if self.frequency_type is FrequencyType.WEEKLY and not self.days_of_week:
            raise ValueError("days_of_week is required for WEEKLY schedules")
        if self.frequency_type is FrequencyType.EVERY_X_HOURS and self.interval_hours is None:
            raise ValueError("interval_hours is required for EVERY_X_HOURS schedules")
        if self.frequency_type is FrequencyType.AS_NEEDED:
            if (
                self.scheduled_time is not None
                or self.days_of_week
                or self.interval_hours is not None
            ):
                raise ValueError("AS_NEEDED schedules cannot include automatic timing fields")
        return self


class ScheduleCreateRequest(ScheduleFields):
    pass


class ScheduleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frequency_type: FrequencyType | None = None
    scheduled_time: time | None = None
    days_of_week: list[DayOfWeek] | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=168)
    start_date: date | None = None
    end_date: date | None = None
    reminder_offset_minutes: int | None = Field(default=None, ge=0, le=10080)
    active: bool | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    user_id: UUID
    frequency_type: FrequencyType
    scheduled_time: time | None
    days_of_week: list[str] | None
    interval_hours: int | None
    start_date: date
    end_date: date | None
    reminder_offset_minutes: int
    active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class DoseLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    medication_id: UUID
    schedule_id: UUID
    scheduled_time: datetime
    actual_taken_time: datetime | None
    status: DoseStatus
    confirmation_method: ConfirmationMethod | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("scheduled_time", "actual_taken_time")
    @classmethod
    def normalize_utc_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class DoseConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_method: ConfirmationMethod
    actual_taken_time: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DoseStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(default=None, max_length=2000)
