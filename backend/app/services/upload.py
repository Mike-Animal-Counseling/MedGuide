from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.caregiver import CaregiverPermission
from app.models.upload import ImagePurpose, UploadedImage
from app.models.user import User
from app.repositories.upload import UploadedImageRepository
from app.schemas.upload import SignedReadResponse, SignedUploadRequest, SignedUploadResponse
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver_authorization import CaregiverAuthorizationService
from app.services.storage import StorageProvider, retention_deadline


class UploadService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        storage: StorageProvider,
        audit: AuditService | NullAuditService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.audit = audit or NullAuditService()
        self.images = UploadedImageRepository(session)
        self.authorization = CaregiverAuthorizationService(session)

    async def create_signed_upload(
        self, actor: User, request: SignedUploadRequest
    ) -> SignedUploadResponse:
        content_type = request.content_type.casefold()
        if content_type not in self.settings.storage_allowed_content_types:
            raise AppError(
                code="invalid_image_content_type",
                message="Image content type is not allowed",
                status_code=422,
            )
        if (
            request.size_bytes is not None
            and request.size_bytes > self.settings.storage_max_upload_bytes
        ):
            raise AppError(
                code="image_too_large",
                message="Image exceeds the configured upload size limit",
                status_code=422,
            )
        patient = await self.authorization.resolve_patient(
            actor,
            request.patient_id,
            required_permission=_write_permission(request.purpose),
        )
        image_id = uuid4()
        object_key = f"users/{patient.id}/images/{image_id}"
        signed = await self.storage.create_signed_upload(
            object_key=object_key,
            content_type=content_type,
            max_size_bytes=self.settings.storage_max_upload_bytes,
            exact_size_bytes=request.size_bytes,
            expires_in_seconds=self.settings.storage_signed_url_expire_seconds,
            retain_until=retention_deadline(self.settings),
        )
        image = await self.images.add(
            UploadedImage(
                id=image_id,
                user_id=patient.id,
                object_key=object_key,
                provider=self.storage.name,
                purpose=request.purpose,
                content_type=content_type,
                size_bytes=request.size_bytes,
            )
        )
        await self.audit.record(
            action="image.uploaded",
            actor_user_id=actor.id,
            target_user_id=patient.id,
            resource_type="uploaded_image",
            resource_id=image.id,
            metadata={"purpose": image.purpose.value, "content_type": image.content_type},
        )
        await self.session.commit()
        await self.session.refresh(image)
        return SignedUploadResponse(
            image_id=image.id,
            upload_url=signed.url,
            upload_fields=signed.fields,
            expires_in_seconds=self.settings.storage_signed_url_expire_seconds,
        )

    async def create_signed_read(self, actor: User, image_id: UUID) -> SignedReadResponse:
        image = await self._authorized_image(actor, image_id, read=True)
        read_url = await self.storage.create_signed_read(
            object_key=image.object_key,
            expires_in_seconds=self.settings.storage_signed_url_expire_seconds,
        )
        return SignedReadResponse(
            image_id=image.id,
            read_url=read_url,
            expires_in_seconds=self.settings.storage_signed_url_expire_seconds,
        )

    async def delete(self, actor: User, image_id: UUID) -> None:
        image = await self._authorized_image(actor, image_id, read=False)
        await self.storage.delete_object(object_key=image.object_key)
        await self.images.soft_delete(image)
        await self.audit.record(
            action="image.deleted",
            actor_user_id=actor.id,
            target_user_id=image.user_id,
            resource_type="uploaded_image",
            resource_id=image.id,
        )
        await self.session.commit()

    async def _authorized_image(self, actor: User, image_id: UUID, *, read: bool) -> UploadedImage:
        image = await self.images.get_active(image_id)
        if image is None:
            raise _not_found()
        if image.provider != self.storage.name:
            raise AppError(
                code="storage_provider_mismatch",
                message="Image storage provider is not currently configured",
                status_code=503,
            )
        required = _read_permission(image.purpose) if read else _write_permission(image.purpose)
        try:
            await self.authorization.resolve_patient(
                actor, image.user_id, required_permission=required
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found() from exc
            raise
        return image


def _read_permission(purpose: ImagePurpose) -> CaregiverPermission:
    if purpose is ImagePurpose.VERIFICATION_IMAGE:
        return CaregiverPermission.FULL_ACCESS
    return CaregiverPermission.VIEW_ONLY


def _write_permission(purpose: ImagePurpose) -> CaregiverPermission:
    if purpose is ImagePurpose.VERIFICATION_IMAGE:
        return CaregiverPermission.FULL_ACCESS
    return CaregiverPermission.MANAGE_MEDICATIONS


def _not_found() -> AppError:
    return AppError(code="image_not_found", message="Image not found", status_code=404)
