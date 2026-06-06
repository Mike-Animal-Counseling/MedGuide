from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "MedGuide AI API"
    app_env: Environment = Environment.LOCAL
    log_level: str = "INFO"
    sentry_dsn: SecretStr | None = None
    sentry_environment: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    api_v1_prefix: str = "/api/v1"
    api_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8081"]
    )
    database_url: str = "postgresql+asyncpg://medguide:change-me@localhost:5432/medguide"
    redis_url: str = "redis://localhost:6379/0"
    database_pool_size: int = Field(default=5, ge=1)
    database_pool_max_overflow: int = Field(default=10, ge=0)
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    jwt_secret: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=365)
    dose_on_time_window_minutes: int = Field(default=30, ge=0, le=1440)
    verification_due_early_minutes: int = Field(default=30, ge=0, le=1440)
    verification_recent_due_minutes: int = Field(default=120, ge=0, le=10080)
    reminder_second_offset_minutes: int = Field(default=15, ge=1, le=1440)
    reminder_escalation_minutes: int = Field(default=30, ge=1, le=10080)
    reminder_missed_cutoff_minutes: int = Field(default=60, ge=1, le=10080)
    notification_retry_max_attempts: int = Field(default=3, ge=1, le=10)
    notification_provider: Literal["unconfigured", "expo"] = "unconfigured"
    expo_push_access_token: SecretStr | None = None
    sms_provider: Literal["disabled"] = "disabled"
    email_provider: Literal["disabled"] = "disabled"
    caregiver_invite_expire_hours: int = Field(default=72, ge=1, le=720)
    caregiver_invite_token_return_enabled: bool = False
    enable_local_dev_storage: bool = False
    enable_test_provider_mocks: bool = False
    storage_provider: Literal["unconfigured", "s3"] = "unconfigured"
    storage_signed_url_expire_seconds: int = Field(default=300, ge=60, le=3600)
    storage_max_upload_bytes: int = Field(default=10_485_760, ge=1, le=104_857_600)
    storage_retention_days: int | None = Field(default=None, ge=1, le=3650)
    storage_allowed_content_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    ocr_provider: Literal["unconfigured", "aws_textract"] = "unconfigured"
    aws_textract_region: str | None = None
    aws_textract_access_key_id: SecretStr | None = None
    aws_textract_secret_access_key: SecretStr | None = None
    image_quality_min_width: int = Field(default=640, ge=1, le=10000)
    image_quality_min_height: int = Field(default=480, ge=1, le=10000)
    image_quality_min_contrast: float = Field(default=20.0, ge=0, le=255)
    vision_provider: Literal["unconfigured", "aws_rekognition"] = "unconfigured"
    aws_rekognition_region: str | None = None
    aws_rekognition_access_key_id: SecretStr | None = None
    aws_rekognition_secret_access_key: SecretStr | None = None

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("storage_allowed_content_types", mode="before")
    @classmethod
    def split_storage_content_types(cls, value: object) -> object:
        if isinstance(value, str):
            return [
                content_type.strip().casefold()
                for content_type in value.split(",")
                if content_type.strip()
            ]
        return value

    @field_validator(
        "jwt_secret",
        "sentry_dsn",
        "expo_push_access_token",
        "s3_access_key_id",
        "s3_secret_access_key",
        "aws_textract_access_key_id",
        "aws_textract_secret_access_key",
        "aws_rekognition_access_key_id",
        "aws_rekognition_secret_access_key",
        mode="before",
    )
    @classmethod
    def empty_secret_to_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator(
        "s3_bucket",
        "s3_region",
        "aws_textract_region",
        "aws_rekognition_region",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("storage_retention_days", mode="before")
    @classmethod
    def empty_int_to_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.app_env is not Environment.PRODUCTION:
            return self

        unsafe_values = ("localhost", "127.0.0.1", "change-me")
        configured_urls = (self.database_url, self.redis_url)
        if any(value in url for value in unsafe_values for url in configured_urls):
            raise ValueError("Production database and Redis URLs must use managed credentials")
        jwt_secret = self.jwt_secret.get_secret_value() if self.jwt_secret is not None else ""
        unsafe_jwt_markers = ("change-me", "replace-with", "example")
        if len(jwt_secret) < 32 or any(marker in jwt_secret for marker in unsafe_jwt_markers):
            raise ValueError(
                "Production JWT secret must be explicitly configured and at least 32 characters"
            )
        if not self.api_cors_origins or "*" in self.api_cors_origins:
            raise ValueError("Production CORS origins must be explicit and non-empty")
        if self.caregiver_invite_token_return_enabled:
            raise ValueError("Production caregiver invite tokens cannot be returned by the API")
        if self.enable_local_dev_storage:
            raise ValueError("Production cannot enable local development storage")
        if self.enable_test_provider_mocks:
            raise ValueError("Production cannot enable test provider mocks")
        if self.storage_provider != "s3":
            raise ValueError("Production storage provider must be configured as s3")
        if not all(
            (
                self.s3_bucket,
                self.s3_region,
                self.s3_access_key_id,
                self.s3_secret_access_key,
            )
        ):
            raise ValueError("Production S3 storage credentials must be explicitly configured")
        if self.ocr_provider != "aws_textract":
            raise ValueError("Production OCR provider must be configured as aws_textract")
        if not all(
            (
                self.aws_textract_region,
                self.aws_textract_access_key_id,
                self.aws_textract_secret_access_key,
            )
        ):
            raise ValueError("Production AWS Textract credentials must be explicitly configured")
        if self.vision_provider != "aws_rekognition":
            raise ValueError("Production vision provider must be configured as aws_rekognition")
        if not all(
            (
                self.aws_rekognition_region,
                self.aws_rekognition_access_key_id,
                self.aws_rekognition_secret_access_key,
            )
        ):
            raise ValueError("Production AWS Rekognition credentials must be explicitly configured")
        if self.notification_provider != "expo":
            raise ValueError("Production notification provider must be configured as expo")
        if self.expo_push_access_token is None:
            raise ValueError("Production Expo push access token must be explicitly configured")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
