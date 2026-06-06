from dataclasses import dataclass
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from anyio import to_thread
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float | None


class OCRProvider(Protocol):
    async def extract_text(self, image_bytes: bytes) -> OCRResult: ...


class ProviderNotConfiguredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="ocr_provider_not_configured",
            message="OCR provider is not configured",
            status_code=503,
        )


class AWSTextractOCRProvider:
    def __init__(self, settings: Settings) -> None:
        if not all(
            (
                settings.aws_textract_region,
                settings.aws_textract_access_key_id,
                settings.aws_textract_secret_access_key,
            )
        ):
            raise ProviderNotConfiguredError()
        access_key = cast(SecretStr, settings.aws_textract_access_key_id)
        secret_key = cast(SecretStr, settings.aws_textract_secret_access_key)
        self.client: Any = boto3.client(
            "textract",
            region_name=settings.aws_textract_region,
            aws_access_key_id=access_key.get_secret_value(),
            aws_secret_access_key=secret_key.get_secret_value(),
        )

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        try:
            response = await to_thread.run_sync(
                lambda: self.client.detect_document_text(Document={"Bytes": image_bytes})
            )
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                code="ocr_provider_unavailable",
                message="OCR provider is temporarily unavailable",
                status_code=503,
            ) from exc
        lines = [
            str(block["Text"]).strip()
            for block in response.get("Blocks", [])
            if block.get("BlockType") == "LINE" and block.get("Text")
        ]
        confidences = [
            float(block["Confidence"]) / 100
            for block in response.get("Blocks", [])
            if block.get("BlockType") == "LINE" and block.get("Confidence") is not None
        ]
        confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
        return OCRResult(text="\n".join(lines), confidence=confidence)


class UnconfiguredOCRProvider:
    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        raise ProviderNotConfiguredError()


def create_ocr_provider(settings: Settings) -> OCRProvider:
    if settings.ocr_provider == "aws_textract":
        return AWSTextractOCRProvider(settings)
    return UnconfiguredOCRProvider()
