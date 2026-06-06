from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings


def test_loads_configuration_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Configured MedGuide API")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://one.example,https://two.example")
    monkeypatch.setenv("READINESS_TIMEOUT_SECONDS", "4.5")
    monkeypatch.setenv("DOSE_ON_TIME_WINDOW_MINUTES", "45")

    settings = Settings()

    assert settings.app_name == "Configured MedGuide API"
    assert settings.api_cors_origins == ["https://one.example", "https://two.example"]
    assert settings.readiness_timeout_seconds == 4.5
    assert settings.dose_on_time_window_minutes == 45


def test_rejects_unsafe_production_configuration() -> None:
    with pytest.raises(ValidationError, match="managed credentials"):
        Settings(app_env=Environment.PRODUCTION)


def test_rejects_empty_production_cors() -> None:
    with pytest.raises(ValidationError, match="CORS origins"):
        Settings(
            app_env=Environment.PRODUCTION,
            database_url="postgresql+asyncpg://user:secret@db.example/medguide",
            redis_url="rediss://user:secret@cache.example/0",
            api_cors_origins=[],
            jwt_secret="a-production-jwt-secret-that-is-long-enough",
        )


def test_rejects_placeholder_production_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT secret"):
        Settings(
            app_env=Environment.PRODUCTION,
            database_url="postgresql+asyncpg://user:secret@db.example/medguide",
            redis_url="rediss://user:secret@cache.example/0",
            api_cors_origins=["https://app.example"],
            jwt_secret="replace-with-at-least-32-random-characters",
        )


def test_rejects_returning_caregiver_invite_tokens_in_production() -> None:
    with pytest.raises(ValidationError, match="invite tokens"):
        Settings(
            **production_settings_kwargs(),
            caregiver_invite_token_return_enabled=True,
        )


def test_accepts_complete_production_configuration() -> None:
    settings = Settings(**production_settings_kwargs())

    assert settings.app_env is Environment.PRODUCTION
    assert settings.storage_provider == "s3"
    assert settings.ocr_provider == "aws_textract"
    assert settings.vision_provider == "aws_rekognition"
    assert settings.notification_provider == "expo"


def test_rejects_missing_production_jwt_secret() -> None:
    values = production_settings_kwargs()
    values["jwt_secret"] = None

    with pytest.raises(ValidationError, match="JWT secret"):
        Settings(**values)


def test_rejects_local_development_storage_flag_in_production() -> None:
    with pytest.raises(ValidationError, match="local development storage"):
        Settings(**production_settings_kwargs(enable_local_dev_storage=True))


def test_rejects_test_provider_mocks_flag_in_production() -> None:
    with pytest.raises(ValidationError, match="test provider mocks"):
        Settings(**production_settings_kwargs(enable_test_provider_mocks=True))


def test_rejects_unconfigured_production_storage_provider() -> None:
    with pytest.raises(ValidationError, match="storage provider"):
        Settings(**production_settings_kwargs(storage_provider="unconfigured"))


def test_rejects_unconfigured_production_ocr_provider() -> None:
    with pytest.raises(ValidationError, match="OCR provider"):
        Settings(**production_settings_kwargs(ocr_provider="unconfigured"))


def test_empty_optional_provider_values_are_treated_as_missing() -> None:
    settings = Settings(
        jwt_secret="",
        storage_retention_days="",
        s3_bucket="",
        s3_region="",
        s3_access_key_id="",
        s3_secret_access_key="",
        aws_textract_region="",
        aws_textract_access_key_id="",
        aws_textract_secret_access_key="",
        aws_rekognition_region="",
        aws_rekognition_access_key_id="",
        aws_rekognition_secret_access_key="",
        expo_push_access_token="",
    )

    assert settings.jwt_secret is None
    assert settings.storage_retention_days is None
    assert settings.s3_bucket is None
    assert settings.s3_region is None
    assert settings.s3_access_key_id is None
    assert settings.s3_secret_access_key is None
    assert settings.aws_textract_region is None
    assert settings.aws_textract_access_key_id is None
    assert settings.aws_textract_secret_access_key is None
    assert settings.aws_rekognition_region is None
    assert settings.aws_rekognition_access_key_id is None
    assert settings.aws_rekognition_secret_access_key is None
    assert settings.expo_push_access_token is None


def production_settings_kwargs(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "app_env": Environment.PRODUCTION,
        "database_url": "postgresql+asyncpg://user:secret@db.example/medguide",
        "redis_url": "rediss://user:secret@cache.example/0",
        "api_cors_origins": ["https://app.example"],
        "jwt_secret": "a-production-jwt-secret-that-is-long-enough",
        "storage_provider": "s3",
        "s3_bucket": "private-medguide-prod-images",
        "s3_region": "us-east-1",
        "s3_access_key_id": "prod-s3-access-key",
        "s3_secret_access_key": "prod-s3-secret-key",
        "ocr_provider": "aws_textract",
        "aws_textract_region": "us-east-1",
        "aws_textract_access_key_id": "prod-textract-access-key",
        "aws_textract_secret_access_key": "prod-textract-secret-key",
        "vision_provider": "aws_rekognition",
        "aws_rekognition_region": "us-east-1",
        "aws_rekognition_access_key_id": "prod-rekognition-access-key",
        "aws_rekognition_secret_access_key": "prod-rekognition-secret-key",
        "notification_provider": "expo",
        "expo_push_access_token": "prod-expo-push-access-token",
    }
    values.update(overrides)
    return values
