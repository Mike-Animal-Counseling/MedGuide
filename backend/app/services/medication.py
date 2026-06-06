from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import authorization_error
from app.models.caregiver import CaregiverPermission
from app.models.medication import Medication, MedicationSource
from app.models.upload import ImagePurpose
from app.models.user import User, UserRole
from app.repositories.medication import MedicationRepository
from app.repositories.upload import UploadedImageRepository
from app.schemas.medication import MedicationCreateRequest, MedicationUpdateRequest
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver_authorization import CaregiverAuthorizationService


class MedicationService:
    def __init__(
        self, session: AsyncSession, audit: AuditService | NullAuditService | None = None
    ) -> None:
        self.session = session
        self.audit = audit or NullAuditService()
        self.medications = MedicationRepository(session)
        self.images = UploadedImageRepository(session)
        self.authorization = CaregiverAuthorizationService(session)

    async def list_for_user(self, user: User, patient_id: UUID | None = None) -> list[Medication]:
        patient = await self.authorization.resolve_patient(
            user, patient_id, required_permission=CaregiverPermission.MANAGE_MEDICATIONS
        )
        return await self.medications.list_for_user(patient.id)

    async def create(
        self, user: User, request: MedicationCreateRequest, patient_id: UUID | None = None
    ) -> Medication:
        patient = await self.authorization.resolve_patient(
            user, patient_id, required_permission=CaregiverPermission.MANAGE_MEDICATIONS
        )
        if user.role is UserRole.CAREGIVER and request.source is not MedicationSource.CAREGIVER:
            raise authorization_error("Caregiver-created medication must use CAREGIVER source")
        if user.role is UserRole.PATIENT and request.source is MedicationSource.CAREGIVER:
            raise authorization_error(
                "Caregiver medication creation requires a caregiver permission link"
            )
        data = request.model_dump()
        data.pop("confirmed_by")
        await self._validate_image_references(patient.id, data)
        confirmed_by = _validated_confirmer(user, patient, request.confirmed_by)
        medication = await self.medications.add(
            Medication(
                user_id=patient.id,
                **data,
                confirmed_by=confirmed_by,
            )
        )
        await self.audit.record(
            action="medication.created",
            actor_user_id=user.id,
            target_user_id=patient.id,
            resource_type="medication",
            resource_id=medication.id,
            metadata={"source": medication.source.value},
        )
        await self.session.commit()
        await self.session.refresh(medication)
        return medication

    async def get(self, user: User, medication_id: UUID) -> Medication:
        medication = await self.medications.get_active_record(medication_id)
        if medication is None:
            raise _not_found()
        await self._authorize_record(user, medication, manage=True)
        return medication

    async def update(
        self, user: User, medication_id: UUID, request: MedicationUpdateRequest
    ) -> Medication:
        medication = await self.get(user, medication_id)
        changes = request.model_dump(exclude_unset=True)
        await self._validate_image_references(medication.user_id, changes)
        if "confirmed_by" in changes:
            patient = await self.authorization.resolve_patient(
                user,
                medication.user_id,
                required_permission=CaregiverPermission.MANAGE_MEDICATIONS,
            )
            changes["confirmed_by"] = _validated_confirmer(user, patient, request.confirmed_by)
        for field, value in changes.items():
            setattr(medication, field, value)
        if medication.source is MedicationSource.OCR and medication.confirmed_by is None:
            medication.active = False
            if medication.instructions is not None:
                raise AppError(
                    code="medication_confirmation_required",
                    message="OCR instructions require patient confirmation",
                    status_code=409,
                )
        await self.audit.record(
            action="medication.updated",
            actor_user_id=user.id,
            target_user_id=medication.user_id,
            resource_type="medication",
            resource_id=medication.id,
            metadata={"fields": sorted(changes)},
        )
        await self.session.commit()
        await self.session.refresh(medication)
        return medication

    async def delete(self, user: User, medication_id: UUID) -> None:
        medication = await self.get(user, medication_id)
        await self.medications.soft_delete(medication)
        await self.audit.record(
            action="medication.deleted",
            actor_user_id=user.id,
            target_user_id=medication.user_id,
            resource_type="medication",
            resource_id=medication.id,
        )
        await self.session.commit()

    async def _authorize_record(self, user: User, medication: Medication, *, manage: bool) -> None:
        try:
            required = (
                CaregiverPermission.MANAGE_MEDICATIONS if manage else CaregiverPermission.VIEW_ONLY
            )
            await self.authorization.resolve_patient(
                user, medication.user_id, required_permission=required
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found() from exc
            raise

    async def _validate_image_references(self, patient_id: UUID, values: dict[str, object]) -> None:
        expected_purposes = {
            "label_image_id": ImagePurpose.MEDICATION_LABEL,
            "pill_image_id": ImagePurpose.PILL_REFERENCE,
        }
        for field, purpose in expected_purposes.items():
            image_id = values.get(field)
            if image_id is None:
                continue
            image = await self.images.get_active(UUID(str(image_id)))
            if image is None or image.user_id != patient_id or image.purpose is not purpose:
                raise AppError(
                    code="image_not_found",
                    message="Image not found",
                    status_code=404,
                )


def _validated_confirmer(user: User, patient: User, confirmed_by: UUID | None) -> UUID | None:
    if confirmed_by is not None and (user.id != patient.id or confirmed_by != patient.id):
        raise authorization_error("Only the owning patient may confirm this medication")
    return confirmed_by


def _not_found() -> AppError:
    return AppError(code="medication_not_found", message="Medication not found", status_code=404)
