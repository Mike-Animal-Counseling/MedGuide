from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.observability import MetricsService, NullMetricsService, record_event
from app.models.ai_verification import AIVerificationEvent, VerificationResult, VerificationType
from app.models.caregiver import CaregiverPermission
from app.models.upload import ImagePurpose, UploadedImage
from app.models.user import User
from app.repositories.ai_verification import AIVerificationEventRepository
from app.repositories.upload import UploadedImageRepository
from app.schemas.ai import ScanLabelResponse
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver_authorization import CaregiverAuthorizationService
from app.services.image_quality import PillowImageQualityChecker
from app.services.label_parser import parse_label_text
from app.services.ocr import OCRProvider
from app.services.storage import StorageProvider

SAFETY_MESSAGE = "Please confirm the extracted medication information before saving."


class LabelScanService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        storage: StorageProvider,
        ocr: OCRProvider,
        quality_checker: PillowImageQualityChecker,
        audit: AuditService | NullAuditService | None = None,
        metrics: MetricsService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.ocr = ocr
        self.quality_checker = quality_checker
        self.audit = audit or NullAuditService()
        self.metrics = metrics or NullMetricsService()
        self.images = UploadedImageRepository(session)
        self.events = AIVerificationEventRepository(session)
        self.authorization = CaregiverAuthorizationService(session)

    async def scan_label(self, actor: User, image_id: UUID) -> ScanLabelResponse:
        image = await self._authorized_label_image(actor, image_id)
        image_bytes = await self.storage.read_object(
            object_key=image.object_key,
            max_bytes=self.settings.storage_max_upload_bytes,
        )
        quality = await self.quality_checker.check(image_bytes)
        if not quality.readable:
            await self._record_event(
                image=image,
                result=VerificationResult.UNREADABLE_IMAGE,
                visual_features=quality.visual_features,
            )
            return ScanLabelResponse(
                result="UNREADABLE_IMAGE",
                ocr_text=None,
                extracted_fields={},
                confidence_score=None,
                safety_message=SAFETY_MESSAGE,
            )

        ocr_result = await self.ocr.extract_text(image_bytes)
        if not ocr_result.text.strip():
            await self._record_event(
                image=image,
                result=VerificationResult.UNREADABLE_IMAGE,
                visual_features=quality.visual_features,
            )
            return ScanLabelResponse(
                result="UNREADABLE_IMAGE",
                ocr_text=None,
                extracted_fields={},
                confidence_score=ocr_result.confidence,
                safety_message=SAFETY_MESSAGE,
            )
        extracted_fields = parse_label_text(ocr_result.text)
        await self._record_event(
            image=image,
            result=VerificationResult.CAREGIVER_REVIEW_REQUIRED,
            ocr_text=ocr_result.text,
            extracted_fields=extracted_fields,
            visual_features=quality.visual_features,
            confidence_score=ocr_result.confidence,
        )
        return ScanLabelResponse(
            result="LABEL_READ",
            ocr_text=ocr_result.text,
            extracted_fields=extracted_fields,
            confidence_score=ocr_result.confidence,
            safety_message=SAFETY_MESSAGE,
        )

    async def _authorized_label_image(self, actor: User, image_id: UUID) -> UploadedImage:
        image = await self.images.get_active(image_id)
        if image is None or image.purpose is not ImagePurpose.MEDICATION_LABEL:
            raise _not_found()
        if image.provider != self.storage.name:
            raise AppError(
                code="storage_provider_mismatch",
                message="Image storage provider is not currently configured",
                status_code=503,
            )
        try:
            await self.authorization.resolve_patient(
                actor,
                image.user_id,
                required_permission=CaregiverPermission.FULL_ACCESS,
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found() from exc
            raise
        return image

    async def _record_event(
        self,
        *,
        image: UploadedImage,
        result: VerificationResult,
        ocr_text: str | None = None,
        extracted_fields: dict[str, str] | None = None,
        visual_features: dict[str, float | int | str] | None = None,
        confidence_score: float | None = None,
    ) -> None:
        event = await self.events.add(
            AIVerificationEvent(
                user_id=image.user_id,
                image_id=image.id,
                verification_type=VerificationType.LABEL_OCR,
                ocr_text=ocr_text,
                extracted_fields=extracted_fields,
                visual_features=visual_features,
                confidence_score=confidence_score,
                result=result,
                safety_message=SAFETY_MESSAGE,
            )
        )
        await self.audit.record(
            action="ai_verification.created",
            target_user_id=image.user_id,
            resource_type="ai_verification_event",
            resource_id=event.id,
            metadata={
                "verification_type": VerificationType.LABEL_OCR.value,
                "result": result.value,
            },
        )
        record_event(
            self.metrics,
            "ai_scan_completed",
            tags={"result": result.value},
            metadata={
                "image_id": str(image.id),
                "confidence_score": confidence_score,
                "verification_type": VerificationType.LABEL_OCR.value,
            },
        )
        await self.session.commit()


def _not_found() -> AppError:
    return AppError(code="image_not_found", message="Image not found", status_code=404)
