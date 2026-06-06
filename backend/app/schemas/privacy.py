from typing import Any

from pydantic import BaseModel, Field


class PrivacyExportResponse(BaseModel):
    user: dict[str, Any]
    medications: list[dict[str, Any]] = Field(default_factory=list)
    schedules: list[dict[str, Any]] = Field(default_factory=list)
    dose_logs: list[dict[str, Any]] = Field(default_factory=list)
    caregiver_links: list[dict[str, Any]] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    ai_verification_events: list[dict[str, Any]] = Field(default_factory=list)
    notification_events: list[dict[str, Any]] = Field(default_factory=list)
    devices: list[dict[str, Any]] = Field(default_factory=list)
