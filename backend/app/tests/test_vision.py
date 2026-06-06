from typing import Any

import pytest

from app.core.config import Settings
from app.services.vision import (
    AWSRekognitionVisionProvider,
    VisionImageRef,
    VisionProviderNotConfiguredError,
    create_vision_provider,
)


async def test_unconfigured_vision_provider_fails_safely() -> None:
    provider = create_vision_provider(Settings())

    with pytest.raises(VisionProviderNotConfiguredError):
        await provider.extract_features(VisionImageRef(image_bytes=b"image"))


def test_rekognition_adapter_extracts_observable_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRekognitionClient:
        def detect_labels(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["Image"]["Bytes"] == b"image"
            return {
                "Labels": [
                    {"Name": "White", "Confidence": 90},
                    {"Name": "Round", "Confidence": 80},
                    {"Name": "Medication", "Confidence": 70},
                ]
            }

        def detect_text(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "TextDetections": [
                    {"Type": "LINE", "DetectedText": "A1"},
                    {"Type": "WORD", "DetectedText": "ignored"},
                ]
            }

    monkeypatch.setattr(
        "app.services.vision.boto3.client", lambda *args, **kwargs: FakeRekognitionClient()
    )
    provider = AWSRekognitionVisionProvider(
        Settings(
            vision_provider="aws_rekognition",
            aws_rekognition_region="us-east-1",
            aws_rekognition_access_key_id="test-access",
            aws_rekognition_secret_access_key="test-secret",
        )
    )

    async def extract() -> None:
        features = await provider.extract_features(VisionImageRef(image_bytes=b"image"))
        assert features.colors == ("white",)
        assert features.shapes == ("round",)
        assert features.visible_imprint == "A1"
        assert features.provider_confidence == 0.8

    import asyncio

    asyncio.run(extract())


def test_rekognition_missing_credentials_fails_safely() -> None:
    with pytest.raises(VisionProviderNotConfiguredError):
        AWSRekognitionVisionProvider(Settings(vision_provider="aws_rekognition"))
