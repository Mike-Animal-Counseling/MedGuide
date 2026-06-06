from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import DevicePlatform


class DeviceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: DevicePlatform
    push_token: str = Field(min_length=10, max_length=512)

    @field_validator("push_token")
    @classmethod
    def validate_expo_token(cls, value: str) -> str:
        token = value.strip()
        if not (
            (token.startswith("ExpoPushToken[") or token.startswith("ExponentPushToken["))
            and token.endswith("]")
        ):
            raise ValueError("push_token must be a valid Expo push token")
        return token


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: DevicePlatform
    active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
