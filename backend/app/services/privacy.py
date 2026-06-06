from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_verification import AIVerificationEvent
from app.models.audit import AuditLog
from app.models.caregiver import CaregiverLink
from app.models.medication import Medication
from app.models.notification import NotificationEvent, UserDevice
from app.models.schedule import DoseLog, MedicationSchedule
from app.models.upload import UploadedImage
from app.models.user import User
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver import CaregiverService
from app.services.upload import UploadService


class PrivacyService:
    def __init__(
        self,
        session: AsyncSession,
        upload_service: UploadService,
        caregiver_service: CaregiverService,
        audit: AuditService | NullAuditService | None = None,
    ) -> None:
        self.session = session
        self.upload_service = upload_service
        self.caregiver_service = caregiver_service
        self.audit = audit or NullAuditService()

    async def export(self, user: User) -> dict[str, Any]:
        payload = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "timezone": user.timezone,
                "accessibility_preferences": user.accessibility_preferences,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "medications": [_medication(item) for item in await self._list(Medication, user.id)],
            "schedules": [
                _schedule(item) for item in await self._list(MedicationSchedule, user.id)
            ],
            "dose_logs": [_dose_log(item) for item in await self._list(DoseLog, user.id)],
            "images": [_image(item) for item in await self._list(UploadedImage, user.id)],
            "devices": [_device(item) for item in await self._list(UserDevice, user.id)],
            "notification_events": [
                _notification(item) for item in await self._list(NotificationEvent, user.id)
            ],
            "ai_verification_events": [
                _ai_event(item) for item in await self._list(AIVerificationEvent, user.id)
            ],
            "caregiver_links": [
                _caregiver_link(item) for item in await self._caregiver_links(user.id)
            ],
            "audit_logs": [_audit_log(item) for item in await self._audit_logs(user.id)],
        }
        await self.audit.record(
            action="privacy.exported",
            actor_user_id=user.id,
            target_user_id=user.id,
            resource_type="privacy_export",
            resource_id=user.id,
        )
        await self.session.commit()
        return payload

    async def delete_image(self, user: User, image_id: UUID) -> None:
        await self.upload_service.delete(user, image_id)

    async def revoke_caregiver(self, user: User, link_id: UUID) -> None:
        await self.caregiver_service.revoke(user, link_id)

    async def _list(self, model: type[Any], user_id: UUID) -> list[Any]:
        result = await self.session.scalars(select(model).where(model.user_id == user_id))
        return list(result)

    async def _caregiver_links(self, user_id: UUID) -> list[CaregiverLink]:
        result = await self.session.scalars(
            select(CaregiverLink).where(
                (CaregiverLink.patient_id == user_id) | (CaregiverLink.caregiver_id == user_id)
            )
        )
        return list(result)

    async def _audit_logs(self, user_id: UUID) -> list[AuditLog]:
        result = await self.session.scalars(
            select(AuditLog)
            .where((AuditLog.actor_user_id == user_id) | (AuditLog.target_user_id == user_id))
            .order_by(AuditLog.created_at)
        )
        return list(result)


def _medication(item: Medication) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "generic_name": item.generic_name,
        "brand_name": item.brand_name,
        "dosage": item.dosage,
        "form": item.form.value,
        "instructions": item.instructions,
        "active": item.active,
        "deleted_at": _dt(item.deleted_at),
    }


def _schedule(item: MedicationSchedule) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "medication_id": str(item.medication_id),
        "frequency_type": item.frequency_type.value,
        "active": item.active,
    }


def _dose_log(item: DoseLog) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "medication_id": str(item.medication_id),
        "scheduled_time": _dt(item.scheduled_time),
        "actual_taken_time": _dt(item.actual_taken_time),
        "status": item.status.value,
    }


def _image(item: UploadedImage) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "purpose": item.purpose.value,
        "content_type": item.content_type,
        "size_bytes": item.size_bytes,
        "created_at": _dt(item.created_at),
        "deleted_at": _dt(item.deleted_at),
    }


def _device(item: UserDevice) -> dict[str, Any]:
    return {"id": str(item.id), "platform": item.platform.value, "active": item.active}


def _notification(item: NotificationEvent) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "dose_log_id": str(item.dose_log_id) if item.dose_log_id else None,
        "notification_type": item.notification_type.value,
        "channel": item.channel.value,
        "status": item.status.value,
        "created_at": _dt(item.created_at),
        "sent_at": _dt(item.sent_at),
    }


def _ai_event(item: AIVerificationEvent) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "verification_type": item.verification_type.value,
        "result": item.result.value,
        "confidence_score": float(item.confidence_score) if item.confidence_score else None,
        "created_at": _dt(item.created_at),
    }


def _caregiver_link(item: CaregiverLink) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "patient_id": str(item.patient_id),
        "caregiver_id": str(item.caregiver_id) if item.caregiver_id else None,
        "permission_level": item.permission_level.value,
        "status": item.status.value,
    }


def _audit_log(item: AuditLog) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "actor_user_id": str(item.actor_user_id) if item.actor_user_id else None,
        "target_user_id": str(item.target_user_id) if item.target_user_id else None,
        "action": item.action,
        "resource_type": item.resource_type,
        "resource_id": str(item.resource_id) if item.resource_id else None,
        "metadata": item.metadata_,
        "request_id": item.request_id,
        "created_at": _dt(item.created_at),
    }


def _dt(value: Any) -> str | None:
    return value.isoformat() if value is not None else None
