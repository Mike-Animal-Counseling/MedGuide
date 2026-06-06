from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.upload import ImagePurpose


class SignedUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: ImagePurpose
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int | None = Field(default=None, ge=1)
    patient_id: UUID | None = None


class SignedUploadResponse(BaseModel):
    image_id: UUID
    upload_url: str
    upload_fields: dict[str, str]
    expires_in_seconds: int


class SignedReadResponse(BaseModel):
    image_id: UUID
    read_url: str
    expires_in_seconds: int


class UploadedImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    provider: str
    purpose: ImagePurpose
    content_type: str
    size_bytes: int | None
    created_at: datetime
