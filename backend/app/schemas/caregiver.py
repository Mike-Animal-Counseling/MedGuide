from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.caregiver import CaregiverLinkStatus, CaregiverPermission
from app.schemas.schedule import DoseLogResponse, ScheduleResponse
from app.schemas.user import UserResponse


class CaregiverInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caregiver_email: EmailStr
    relationship: str | None = Field(default=None, max_length=200)
    permission_level: CaregiverPermission

    @field_validator("relationship", mode="before")
    @classmethod
    def normalize_relationship(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CaregiverInviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    caregiver_email: EmailStr
    relationship: str | None
    permission_level: CaregiverPermission
    status: CaregiverLinkStatus
    invite_expires_at: datetime
    created_at: datetime
    invite_token: str | None = None


class CaregiverAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invite_token: str = Field(min_length=32, max_length=512)


class CaregiverLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    caregiver_id: UUID | None
    caregiver_email: EmailStr
    relationship: str | None
    permission_level: CaregiverPermission
    status: CaregiverLinkStatus
    created_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class LinkedPatientResponse(BaseModel):
    link: CaregiverLinkResponse
    patient: UserResponse


class PatientTodayResponse(BaseModel):
    patient_id: UUID
    schedules: list[ScheduleResponse]
    dose_logs: list[DoseLogResponse]
