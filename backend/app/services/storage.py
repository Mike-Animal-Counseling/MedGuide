from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from anyio import to_thread
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class SignedUpload:
    url: str
    fields: dict[str, str]


class StorageProvider(Protocol):
    name: str

    async def create_signed_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        max_size_bytes: int,
        exact_size_bytes: int | None,
        expires_in_seconds: int,
        retain_until: datetime | None,
    ) -> SignedUpload: ...

    async def create_signed_read(self, *, object_key: str, expires_in_seconds: int) -> str: ...

    async def read_object(self, *, object_key: str, max_bytes: int) -> bytes: ...

    async def delete_object(self, *, object_key: str) -> None: ...


class S3StorageProvider:
    name = "s3"

    def __init__(self, settings: Settings) -> None:
        if not all(
            (
                settings.s3_bucket,
                settings.s3_region,
                settings.s3_access_key_id,
                settings.s3_secret_access_key,
            )
        ):
            raise AppError(
                code="storage_configuration_error",
                message="S3 storage credentials are not configured",
                status_code=503,
            )
        self.bucket = settings.s3_bucket
        access_key = cast(SecretStr, settings.s3_access_key_id)
        secret_key = cast(SecretStr, settings.s3_secret_access_key)
        self.client: Any = boto3.client(
            "s3",
            region_name=settings.s3_region,
            aws_access_key_id=access_key.get_secret_value(),
            aws_secret_access_key=secret_key.get_secret_value(),
        )

    async def create_signed_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        max_size_bytes: int,
        exact_size_bytes: int | None,
        expires_in_seconds: int,
        retain_until: datetime | None,
    ) -> SignedUpload:
        fields = {"Content-Type": content_type}
        conditions: list[object] = [{"Content-Type": content_type}]
        minimum_size = exact_size_bytes or 1
        maximum_size = exact_size_bytes or max_size_bytes
        conditions.append(["content-length-range", minimum_size, maximum_size])
        if retain_until is not None:
            retain_value = retain_until.astimezone(UTC).isoformat()
            fields["x-amz-meta-retain-until"] = retain_value
            conditions.append({"x-amz-meta-retain-until": retain_value})
        try:
            response = await to_thread.run_sync(
                lambda: self.client.generate_presigned_post(
                    Bucket=self.bucket,
                    Key=object_key,
                    Fields=fields,
                    Conditions=conditions,
                    ExpiresIn=expires_in_seconds,
                )
            )
        except (BotoCoreError, ClientError) as exc:
            raise _storage_unavailable() from exc
        return SignedUpload(url=str(response["url"]), fields=dict(response["fields"]))

    async def create_signed_read(self, *, object_key: str, expires_in_seconds: int) -> str:
        try:
            return str(
                await to_thread.run_sync(
                    lambda: self.client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": self.bucket, "Key": object_key},
                        ExpiresIn=expires_in_seconds,
                    )
                )
            )
        except (BotoCoreError, ClientError) as exc:
            raise _storage_unavailable() from exc

    async def delete_object(self, *, object_key: str) -> None:
        try:
            await to_thread.run_sync(
                lambda: self.client.delete_object(Bucket=self.bucket, Key=object_key)
            )
        except (BotoCoreError, ClientError) as exc:
            raise _storage_unavailable() from exc

    async def read_object(self, *, object_key: str, max_bytes: int) -> bytes:
        try:
            response = await to_thread.run_sync(
                lambda: self.client.get_object(Bucket=self.bucket, Key=object_key)
            )
            if int(response["ContentLength"]) > max_bytes:
                raise _image_too_large()
            data = bytes(await to_thread.run_sync(lambda: response["Body"].read(max_bytes + 1)))
            if len(data) > max_bytes:
                raise _image_too_large()
            return data
        except AppError:
            raise
        except (BotoCoreError, ClientError, KeyError, OSError) as exc:
            raise _storage_unavailable() from exc


class UnconfiguredStorageProvider:
    name = "unconfigured"

    async def create_signed_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        max_size_bytes: int,
        exact_size_bytes: int | None,
        expires_in_seconds: int,
        retain_until: datetime | None,
    ) -> SignedUpload:
        raise _storage_unconfigured()

    async def create_signed_read(self, *, object_key: str, expires_in_seconds: int) -> str:
        raise _storage_unconfigured()

    async def read_object(self, *, object_key: str, max_bytes: int) -> bytes:
        raise _storage_unconfigured()

    async def delete_object(self, *, object_key: str) -> None:
        raise _storage_unconfigured()


def create_storage_provider(settings: Settings) -> StorageProvider:
    if settings.storage_provider == "s3":
        return S3StorageProvider(settings)
    return UnconfiguredStorageProvider()


def retention_deadline(settings: Settings) -> datetime | None:
    if settings.storage_retention_days is None:
        return None
    return datetime.now(UTC) + timedelta(days=settings.storage_retention_days)


def _storage_unconfigured() -> AppError:
    return AppError(
        code="storage_provider_unconfigured",
        message="Private image storage is not configured",
        status_code=503,
    )


def _storage_unavailable() -> AppError:
    return AppError(
        code="storage_provider_unavailable",
        message="Private image storage is temporarily unavailable",
        status_code=503,
    )


def _image_too_large() -> AppError:
    return AppError(
        code="image_too_large",
        message="Stored image exceeds the configured processing size limit",
        status_code=422,
    )
