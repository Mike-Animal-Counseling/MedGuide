import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$")


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone") from exc
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    role: UserRole = UserRole.PATIENT
    timezone: str = "UTC"
    accessibility_preferences: dict[str, Any] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: EmailStr) -> str:
        return normalize_email(str(value))

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError(
                "Password must include lowercase, uppercase, number, and special character"
            )
        return value

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("role")
    @classmethod
    def reject_public_admin_registration(cls, value: UserRole) -> UserRole:
        if value is UserRole.ADMIN:
            raise ValueError("ADMIN users cannot be created through public registration")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone_value(cls, value: str) -> str:
        return validate_timezone(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    access_expires_in: int
    refresh_expires_in: int
