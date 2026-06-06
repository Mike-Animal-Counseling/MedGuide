from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.services.ocr import AWSTextractOCRProvider, ProviderNotConfiguredError, create_ocr_provider


async def test_unconfigured_ocr_provider_fails_safely() -> None:
    provider = create_ocr_provider(Settings())

    with pytest.raises(ProviderNotConfiguredError):
        await provider.extract_text(b"image")


def test_textract_adapter_extracts_lines_and_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeTextractClient:
        def detect_document_text(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["Document"]["Bytes"] == b"image"
            return {
                "Blocks": [
                    {"BlockType": "LINE", "Text": "ExampleMed", "Confidence": 90},
                    {"BlockType": "WORD", "Text": "ignored", "Confidence": 100},
                    {"BlockType": "LINE", "Text": "10 mg", "Confidence": 80},
                ]
            }

    monkeypatch.setattr(
        "app.services.ocr.boto3.client", lambda *args, **kwargs: FakeTextractClient()
    )
    provider = AWSTextractOCRProvider(
        Settings(
            ocr_provider="aws_textract",
            aws_textract_region="us-east-1",
            aws_textract_access_key_id="test-access",
            aws_textract_secret_access_key="test-secret",
        )
    )

    async def extract() -> None:
        result = await provider.extract_text(b"image")
        assert result.text == "ExampleMed\n10 mg"
        assert result.confidence == 0.85

    import asyncio

    asyncio.run(extract())


def test_textract_missing_credentials_fails_safely() -> None:
    with pytest.raises(AppError, match="not configured"):
        AWSTextractOCRProvider(Settings(ocr_provider="aws_textract"))
