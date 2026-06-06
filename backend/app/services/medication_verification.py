from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import UUID

from anyio import to_thread
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.observability import MetricsService, NullMetricsService, record_event
from app.models.ai_verification import AIVerificationEvent, VerificationResult, VerificationType
from app.models.caregiver import CaregiverPermission
from app.models.medication import Medication
from app.models.schedule import DoseLog, DoseStatus
from app.models.upload import ImagePurpose, UploadedImage
from app.models.user import User
from app.repositories.ai_verification import AIVerificationEventRepository
from app.repositories.medication import MedicationRepository
from app.repositories.schedule import DoseLogRepository
from app.repositories.upload import UploadedImageRepository
from app.schemas.ai import VerifyMedicationResponse
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver_authorization import CaregiverAuthorizationService
from app.services.image_quality import ImageQualityService
from app.services.storage import StorageProvider
from app.services.vision import VisionImageRef, VisionProvider, VisualFeatures


@dataclass(frozen=True)
class VerificationScore:
    confidence: float
    explicit_conflict: bool
    evidence: dict[str, Any]


class MedicationVerificationScorer:
    _WEIGHTS = {"color": 0.25, "shape": 0.25, "imprint": 0.35, "reference": 0.15}

    def score(
        self,
        features: VisualFeatures,
        medication: Medication,
        reference_similarity: float | None = None,
    ) -> VerificationScore:
        evidence: dict[str, Any] = {}
        weighted_score = 0.0
        available_weight = 0.0
        explicit_conflict = False

        for field, expected, observed in (
            ("color", medication.pill_color, features.colors),
            ("shape", medication.pill_shape, features.shapes),
        ):
            if expected:
                available_weight += self._WEIGHTS[field]
                matched = _normalize(expected) in {_normalize(value) for value in observed}
                evidence[field] = {"matched": matched}
                weighted_score += self._WEIGHTS[field] if matched else 0
                explicit_conflict = explicit_conflict or bool(observed and not matched)
        if medication.imprint:
            available_weight += self._WEIGHTS["imprint"]
            matched = _normalize(medication.imprint) == _normalize(features.visible_imprint or "")
            evidence["imprint"] = {"matched": matched}
            weighted_score += self._WEIGHTS["imprint"] if matched else 0
            explicit_conflict = explicit_conflict or bool(features.visible_imprint and not matched)
        if reference_similarity is not None:
            available_weight += self._WEIGHTS["reference"]
            evidence["reference_similarity"] = reference_similarity
            weighted_score += self._WEIGHTS["reference"] * reference_similarity
            explicit_conflict = explicit_conflict or reference_similarity < 0.35

        confidence = weighted_score / available_weight if available_weight else 0.0
        return VerificationScore(
            confidence=round(confidence, 4),
            explicit_conflict=explicit_conflict,
            evidence=evidence,
        )


class SafetyMessageService:
    _MESSAGES = {
        VerificationResult.MATCH_LIKELY: (
            "This appears to match your scheduled medication, but please confirm with the label "
            "or caregiver if unsure."
        ),
        VerificationResult.MATCH_UNCERTAIN: (
            "I am not fully sure this appears to match your scheduled medication. Please check "
            "the label again or contact your caregiver."
        ),
        VerificationResult.NO_MATCH: (
            "This does not appear to match the scheduled medication. Please do not take it based "
            "on this result; check the label or contact your caregiver."
        ),
        VerificationResult.UNREADABLE_IMAGE: (
            "I cannot read this image clearly. Please retake the photo and confirm with the label "
            "or caregiver."
        ),
        VerificationResult.CAREGIVER_REVIEW_REQUIRED: (
            "I cannot confirm this medication. Please do not rely on this result alone. "
            "Please contact your caregiver."
        ),
    }

    def build(self, result: VerificationResult, confidence: float | None) -> str:
        return self._MESSAGES[result]


class MedicationVerificationService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        storage: StorageProvider,
        vision: VisionProvider,
        quality_checker: ImageQualityService,
        audit: AuditService | NullAuditService | None = None,
        metrics: MetricsService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.vision = vision
        self.quality_checker = quality_checker
        self.audit = audit or NullAuditService()
        self.metrics = metrics or NullMetricsService()
        self.dose_logs = DoseLogRepository(session)
        self.medications = MedicationRepository(session)
        self.images = UploadedImageRepository(session)
        self.events = AIVerificationEventRepository(session)
        self.authorization = CaregiverAuthorizationService(session)
        self.scorer = MedicationVerificationScorer()
        self.messages = SafetyMessageService()

    async def verify(
        self,
        actor: User,
        *,
        dose_log_id: UUID,
        image_id: UUID,
        verification_type: VerificationType,
    ) -> VerifyMedicationResponse:
        dose_log = await self._authorized_due_dose(actor, dose_log_id)
        medication = await self.medications.get_for_user(dose_log.medication_id, dose_log.user_id)
        if medication is None or not medication.active:
            raise AppError(
                code="medication_unavailable",
                message="Scheduled medication is unavailable",
                status_code=409,
            )
        image = await self._authorized_image(actor, image_id, dose_log.user_id)
        image_bytes = await self._read(image)
        quality = await self.quality_checker.assess(image_bytes)
        if not quality.readable:
            return await self._record_and_respond(
                dose_log=dose_log,
                medication=medication,
                image=image,
                verification_type=verification_type,
                result=VerificationResult.UNREADABLE_IMAGE,
                confidence=None,
                visual_features=quality.visual_features,
            )

        features = await self.vision.extract_features(VisionImageRef(image_bytes=image_bytes))
        reference_similarity = await self._reference_similarity(
            medication, verification_type, image_bytes
        )
        score = self.scorer.score(features, medication, reference_similarity)
        result = self._classify(score)
        return await self._record_and_respond(
            dose_log=dose_log,
            medication=medication,
            image=image,
            verification_type=verification_type,
            result=result,
            confidence=score.confidence,
            visual_features={**quality.visual_features, **features.as_dict()},
            model_output={"scoring_evidence": score.evidence},
        )

    async def _authorized_due_dose(self, actor: User, dose_log_id: UUID) -> DoseLog:
        dose_log = await self.dose_logs.get_record(dose_log_id)
        if dose_log is None:
            raise _not_found("dose_log_not_found", "Dose log not found")
        try:
            await self.authorization.resolve_patient(
                actor,
                dose_log.user_id,
                required_permission=CaregiverPermission.FULL_ACCESS,
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found("dose_log_not_found", "Dose log not found") from exc
            raise
        if dose_log.status is not DoseStatus.PENDING:
            raise AppError(
                code="dose_log_not_pending",
                message="Only a pending dose can be verified",
                status_code=409,
            )
        scheduled = _aware_utc(dose_log.scheduled_time)
        now = datetime.now(UTC)
        if not (
            scheduled - timedelta(minutes=self.settings.verification_due_early_minutes)
            <= now
            <= scheduled + timedelta(minutes=self.settings.verification_recent_due_minutes)
        ):
            raise AppError(
                code="dose_not_currently_due",
                message=(
                    "Medication verification is only available for a currently or recently due dose"
                ),
                status_code=409,
            )
        return dose_log

    async def _authorized_image(
        self, actor: User, image_id: UUID, patient_id: UUID
    ) -> UploadedImage:
        image = await self.images.get_active(image_id)
        if image is None or image.purpose is not ImagePurpose.VERIFICATION_IMAGE:
            raise _not_found("image_not_found", "Image not found")
        if image.user_id != patient_id or image.provider != self.storage.name:
            raise _not_found("image_not_found", "Image not found")
        try:
            await self.authorization.resolve_patient(
                actor, image.user_id, required_permission=CaregiverPermission.FULL_ACCESS
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found("image_not_found", "Image not found") from exc
            raise
        return image

    async def _read(self, image: UploadedImage) -> bytes:
        return await self.storage.read_object(
            object_key=image.object_key,
            max_bytes=self.settings.storage_max_upload_bytes,
        )

    async def _reference_similarity(
        self,
        medication: Medication,
        verification_type: VerificationType,
        captured_bytes: bytes,
    ) -> float | None:
        reference_id = (
            medication.pill_image_id
            if verification_type is VerificationType.PILL_VERIFY
            else medication.label_image_id
        )
        if reference_id is None:
            return None
        image = await self.images.get_active(reference_id)
        if image is None or image.provider != self.storage.name:
            return None
        return await to_thread.run_sync(
            _histogram_similarity, captured_bytes, await self._read(image)
        )

    def _classify(self, score: VerificationScore) -> VerificationResult:
        if score.confidence >= 0.85:
            return VerificationResult.MATCH_LIKELY
        if score.confidence >= 0.60:
            return VerificationResult.MATCH_UNCERTAIN
        if score.explicit_conflict:
            return VerificationResult.NO_MATCH
        return VerificationResult.CAREGIVER_REVIEW_REQUIRED

    async def _record_and_respond(
        self,
        *,
        dose_log: DoseLog,
        medication: Medication,
        image: UploadedImage,
        verification_type: VerificationType,
        result: VerificationResult,
        confidence: float | None,
        visual_features: dict[str, Any],
        model_output: dict[str, Any] | None = None,
    ) -> VerifyMedicationResponse:
        message = self.messages.build(result, confidence)
        event = await self.events.add(
            AIVerificationEvent(
                user_id=dose_log.user_id,
                medication_id=medication.id,
                dose_log_id=dose_log.id,
                image_id=image.id,
                verification_type=verification_type,
                visual_features=visual_features,
                model_output=model_output,
                confidence_score=confidence,
                result=result,
                safety_message=message,
            )
        )
        await self.audit.record(
            action="ai_verification.created",
            actor_user_id=None,
            target_user_id=dose_log.user_id,
            resource_type="ai_verification_event",
            resource_id=event.id,
            metadata={"verification_type": verification_type.value, "result": result.value},
        )
        record_event(
            self.metrics,
            "ai_verify_completed",
            tags={"result": result.value, "verification_type": verification_type.value},
            metadata={
                "dose_log_id": str(dose_log.id),
                "image_id": str(image.id),
                "confidence_score": confidence,
            },
        )
        await self.session.commit()
        return VerifyMedicationResponse(
            result=result,
            confidence_score=confidence,
            requires_confirmation=True,
            safety_message=message,
        )


def _histogram_similarity(captured_bytes: bytes, reference_bytes: bytes) -> float | None:
    try:
        with Image.open(BytesIO(captured_bytes)) as captured:
            captured_histogram = captured.convert("RGB").resize((64, 64)).histogram()
        with Image.open(BytesIO(reference_bytes)) as reference:
            reference_histogram = reference.convert("RGB").resize((64, 64)).histogram()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return None
    total = sum(captured_histogram)
    if total == 0:
        return None
    intersection = sum(
        min(left, right)
        for left, right in zip(captured_histogram, reference_histogram, strict=True)
    )
    return round(intersection / total, 4)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _not_found(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=404)
