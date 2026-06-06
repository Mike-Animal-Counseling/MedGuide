from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from anyio import to_thread
from PIL import Image, ImageStat, UnidentifiedImageError

from app.core.config import Settings


@dataclass(frozen=True)
class ImageQualityResult:
    readable: bool
    visual_features: dict[str, float | int | str]


class ImageQualityService(Protocol):
    async def assess(self, image_bytes: bytes) -> ImageQualityResult: ...


class PillowImageQualityChecker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def check(self, image_bytes: bytes) -> ImageQualityResult:
        return await self.assess(image_bytes)

    async def assess(self, image_bytes: bytes) -> ImageQualityResult:
        return await to_thread.run_sync(self._check_sync, image_bytes)

    def _check_sync(self, image_bytes: bytes) -> ImageQualityResult:
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                image.verify()
            with Image.open(BytesIO(image_bytes)) as image:
                width, height = image.size
                grayscale = image.convert("L")
                contrast = float(ImageStat.Stat(grayscale).stddev[0])
                features: dict[str, float | int | str] = {
                    "width": width,
                    "height": height,
                    "contrast": round(contrast, 2),
                    "format": image.format or "unknown",
                }
                readable = (
                    width >= self.settings.image_quality_min_width
                    and height >= self.settings.image_quality_min_height
                    and contrast >= self.settings.image_quality_min_contrast
                )
                return ImageQualityResult(readable=readable, visual_features=features)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
            return ImageQualityResult(
                readable=False,
                visual_features={"quality_error": "image_decode_failed"},
            )
