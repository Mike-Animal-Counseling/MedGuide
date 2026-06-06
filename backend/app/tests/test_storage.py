from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings
from app.core.errors import AppError
from app.services.storage import S3StorageProvider, create_storage_provider


def production_settings(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "app_env": Environment.PRODUCTION,
        "database_url": "postgresql+asyncpg://user:secret@db.example/medguide",
        "redis_url": "rediss://user:secret@cache.example/0",
        "api_cors_origins": ["https://app.example"],
        "jwt_secret": "a-production-jwt-secret-that-is-long-enough",
    }
    values.update(overrides)
    return values


def configured_storage() -> dict[str, str]:
    return {
        "storage_provider": "s3",
        "s3_bucket": "private-medguide",
        "s3_region": "us-east-1",
        "s3_access_key_id": "test-access-key",
        "s3_secret_access_key": "test-secret-key",
    }


def configured_ocr() -> dict[str, str]:
    return {
        "ocr_provider": "aws_textract",
        "aws_textract_region": "us-east-1",
        "aws_textract_access_key_id": "test-access-key",
        "aws_textract_secret_access_key": "test-secret-key",
    }


def test_production_config_without_s3_credentials_fails_safely() -> None:
    with pytest.raises(ValidationError, match="storage provider"):
        Settings(**production_settings())

    with pytest.raises(ValidationError, match="S3 storage credentials"):
        Settings(**production_settings(storage_provider="s3"))


def test_production_config_without_ocr_provider_fails_safely() -> None:
    with pytest.raises(ValidationError, match="OCR provider"):
        Settings(**production_settings(**configured_storage()))

    with pytest.raises(ValidationError, match="Textract credentials"):
        Settings(**production_settings(**configured_storage(), ocr_provider="aws_textract"))


def test_production_config_without_vision_provider_fails_safely() -> None:
    with pytest.raises(ValidationError, match="vision provider"):
        Settings(**production_settings(**configured_storage(), **configured_ocr()))

    with pytest.raises(ValidationError, match="Rekognition credentials"):
        Settings(
            **production_settings(
                **configured_storage(),
                **configured_ocr(),
                vision_provider="aws_rekognition",
            )
        )


def test_s3_provider_generates_signed_operations_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    class FakeS3Client:
        def generate_presigned_post(self, **kwargs: Any) -> dict[str, Any]:
            calls["post"] = kwargs
            return {"url": "https://signed-upload.example", "fields": {"key": kwargs["Key"]}}

        def generate_presigned_url(self, operation: str, **kwargs: Any) -> str:
            calls["read"] = (operation, kwargs)
            return "https://signed-read.example"

        def delete_object(self, **kwargs: Any) -> None:
            calls["delete"] = kwargs

        def get_object(self, **kwargs: Any) -> dict[str, Any]:
            from io import BytesIO

            calls["get"] = kwargs
            return {"ContentLength": 3, "Body": BytesIO(b"img")}

    monkeypatch.setattr("app.services.storage.boto3.client", lambda *args, **kwargs: FakeS3Client())
    settings = Settings(
        storage_provider="s3",
        s3_bucket="private-medguide",
        s3_region="us-east-1",
        s3_access_key_id="test-access-key",
        s3_secret_access_key="test-secret-key",
    )
    provider = create_storage_provider(settings)
    assert isinstance(provider, S3StorageProvider)

    async def exercise() -> None:
        upload = await provider.create_signed_upload(
            object_key="users/id/images/id",
            content_type="image/jpeg",
            max_size_bytes=1000,
            exact_size_bytes=500,
            expires_in_seconds=300,
            retain_until=None,
        )
        read = await provider.create_signed_read(
            object_key="users/id/images/id", expires_in_seconds=300
        )
        image_bytes = await provider.read_object(object_key="users/id/images/id", max_bytes=100)
        await provider.delete_object(object_key="users/id/images/id")
        assert upload.url == "https://signed-upload.example"
        assert read == "https://signed-read.example"
        assert image_bytes == b"img"

    import asyncio

    asyncio.run(exercise())
    assert calls["post"]["Conditions"][-1] == ["content-length-range", 500, 500]
    assert calls["read"][0] == "get_object"
    assert calls["delete"]["Bucket"] == "private-medguide"


async def test_unconfigured_storage_provider_fails_safely() -> None:
    provider = create_storage_provider(Settings())

    with pytest.raises(AppError, match="not configured"):
        await provider.create_signed_read(object_key="private-key", expires_in_seconds=300)
