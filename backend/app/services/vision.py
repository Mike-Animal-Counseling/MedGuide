from dataclasses import asdict, dataclass
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from anyio import to_thread
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class VisionImageRef:
    image_bytes: bytes


@dataclass(frozen=True)
class VisualFeatures:
    colors: tuple[str, ...] = ()
    shapes: tuple[str, ...] = ()
    visible_imprint: str | None = None
    label_text: str | None = None
    provider_confidence: float | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class VisionProvider(Protocol):
    async def extract_features(self, image_ref: VisionImageRef) -> VisualFeatures: ...


class VisionProviderNotConfiguredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="vision_provider_not_configured",
            message="Vision provider is not configured",
            status_code=503,
        )


class AWSRekognitionVisionProvider:
    _COLORS = frozenset(
        {
            "black",
            "blue",
            "brown",
            "gray",
            "green",
            "orange",
            "pink",
            "purple",
            "red",
            "white",
            "yellow",
        }
    )
    _SHAPES = frozenset(
        {"capsule", "diamond", "oblong", "oval", "rectangle", "round", "square", "triangle"}
    )

    def __init__(self, settings: Settings) -> None:
        if not all(
            (
                settings.aws_rekognition_region,
                settings.aws_rekognition_access_key_id,
                settings.aws_rekognition_secret_access_key,
            )
        ):
            raise VisionProviderNotConfiguredError()
        access_key = cast(SecretStr, settings.aws_rekognition_access_key_id)
        secret_key = cast(SecretStr, settings.aws_rekognition_secret_access_key)
        self.client: Any = boto3.client(
            "rekognition",
            region_name=settings.aws_rekognition_region,
            aws_access_key_id=access_key.get_secret_value(),
            aws_secret_access_key=secret_key.get_secret_value(),
        )

    async def extract_features(self, image_ref: VisionImageRef) -> VisualFeatures:
        try:
            labels, text = await to_thread.run_sync(
                lambda: (
                    self.client.detect_labels(
                        Image={"Bytes": image_ref.image_bytes},
                        MaxLabels=50,
                        MinConfidence=60,
                    ),
                    self.client.detect_text(Image={"Bytes": image_ref.image_bytes}),
                )
            )
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                code="vision_provider_unavailable",
                message="Vision provider is temporarily unavailable",
                status_code=503,
            ) from exc

        label_values = {
            str(label.get("Name", "")).strip().casefold()
            for label in labels.get("Labels", [])
            if label.get("Name")
        }
        detected_lines = [
            str(item["DetectedText"]).strip()
            for item in text.get("TextDetections", [])
            if item.get("Type") == "LINE" and item.get("DetectedText")
        ]
        confidences = [
            float(label["Confidence"]) / 100
            for label in labels.get("Labels", [])
            if label.get("Confidence") is not None
        ]
        return VisualFeatures(
            colors=tuple(sorted(label_values & self._COLORS)),
            shapes=tuple(sorted(label_values & self._SHAPES)),
            visible_imprint=detected_lines[0] if detected_lines else None,
            label_text="\n".join(detected_lines) or None,
            provider_confidence=round(sum(confidences) / len(confidences), 4)
            if confidences
            else None,
        )


class UnconfiguredVisionProvider:
    async def extract_features(self, image_ref: VisionImageRef) -> VisualFeatures:
        raise VisionProviderNotConfiguredError()


def create_vision_provider(settings: Settings) -> VisionProvider:
    if settings.vision_provider == "aws_rekognition":
        return AWSRekognitionVisionProvider(settings)
    return UnconfiguredVisionProvider()
