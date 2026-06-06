import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Environment, Settings
from app.core.errors import AppError
from app.core.security import authorization_error, hash_token
from app.models.caregiver import CaregiverLink, CaregiverLinkStatus
from app.models.schedule import DoseLog
from app.models.user import User, UserRole
from app.repositories.caregiver import CaregiverLinkRepository
from app.repositories.schedule import DoseLogRepository
from app.repositories.user import UserRepository
from app.schemas.caregiver import (
    CaregiverAcceptRequest,
    CaregiverInviteRequest,
    LinkedPatientResponse,
    PatientTodayResponse,
)
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver_authorization import CaregiverAuthorizationService
from app.services.notification import NotificationService
from app.services.schedule import DoseLogService, ScheduleService


class CaregiverService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        notifications: NotificationService,
        audit: AuditService | NullAuditService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.notifications = notifications
        self.audit = audit or NullAuditService()
        self.links = CaregiverLinkRepository(session)
        self.users = UserRepository(session)

    async def invite(
        self, patient: User, request: CaregiverInviteRequest
    ) -> tuple[CaregiverLink, str | None]:
        _require_role(patient, UserRole.PATIENT)
        caregiver_email = str(request.caregiver_email)
        if caregiver_email == patient.email:
            raise AppError(
                code="invalid_caregiver_invite",
                message="A patient cannot invite their own account",
                status_code=422,
            )
        existing = await self.links.get_unrevoked_for_email(patient.id, caregiver_email)
        if existing is not None:
            expires_at = _as_utc(existing.invite_expires_at)
            if existing.status is CaregiverLinkStatus.PENDING and expires_at <= datetime.now(UTC):
                await self.links.revoke(existing)
            else:
                raise AppError(
                    code="caregiver_link_conflict",
                    message="An active or pending caregiver link already exists",
                    status_code=409,
                )
        invite_token = secrets.token_urlsafe(32)
        link = await self.links.add(
            CaregiverLink(
                patient_id=patient.id,
                caregiver_email=caregiver_email,
                relationship=request.relationship,
                permission_level=request.permission_level,
                status=CaregiverLinkStatus.PENDING,
                invite_token_hash=hash_token(invite_token),
                invite_expires_at=datetime.now(UTC)
                + timedelta(hours=self.settings.caregiver_invite_expire_hours),
            )
        )
        return_token = (
            self.settings.app_env is not Environment.PRODUCTION
            and self.settings.caregiver_invite_token_return_enabled
        )
        if not return_token:
            await self.notifications.send_caregiver_invite(
                caregiver_email=request.caregiver_email,
                patient_name=patient.full_name,
                invite_token=invite_token,
            )
        await self.audit.record(
            action="caregiver.invited",
            actor_user_id=patient.id,
            target_user_id=patient.id,
            resource_type="caregiver_link",
            resource_id=link.id,
            metadata={"permission_level": link.permission_level.value},
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if not _is_link_conflict(exc):
                raise
            raise AppError(
                code="caregiver_link_conflict",
                message="An active or pending caregiver link already exists",
                status_code=409,
            ) from exc
        await self.session.refresh(link)
        return link, invite_token if return_token else None

    async def accept(self, caregiver: User, request: CaregiverAcceptRequest) -> CaregiverLink:
        _require_role(caregiver, UserRole.CAREGIVER)
        link = await self.links.get_pending_by_token_hash(hash_token(request.invite_token))
        if link is None:
            raise AppError(code="invalid_invite", message="Invite is invalid", status_code=400)
        expires_at = _as_utc(link.invite_expires_at)
        if expires_at <= datetime.now(UTC):
            await self.links.revoke(link)
            await self.session.commit()
            raise AppError(code="expired_invite", message="Invite has expired", status_code=400)
        if link.caregiver_email != caregiver.email:
            raise AppError(code="invalid_invite", message="Invite is invalid", status_code=400)
        link.caregiver_id = caregiver.id
        link.status = CaregiverLinkStatus.ACTIVE
        link.accepted_at = datetime.now(UTC)
        await self.audit.record(
            action="caregiver.accepted",
            actor_user_id=caregiver.id,
            target_user_id=link.patient_id,
            resource_type="caregiver_link",
            resource_id=link.id,
        )
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def list_patients(self, caregiver: User) -> list[LinkedPatientResponse]:
        _require_role(caregiver, UserRole.CAREGIVER)
        rows = await self.links.list_active_patients(caregiver.id)
        for link, patient in rows:
            await self.audit.record(
                action="caregiver.viewed_patient_data",
                actor_user_id=caregiver.id,
                target_user_id=patient.id,
                resource_type="caregiver_link",
                resource_id=link.id,
                metadata={"view": "patients"},
            )
        await self.session.commit()
        return [LinkedPatientResponse(link=link, patient=patient) for link, patient in rows]

    async def today(self, caregiver: User, patient_id: UUID) -> PatientTodayResponse:
        patient = await CaregiverAuthorizationService(self.session).resolve_patient(
            caregiver, patient_id
        )
        await self.audit.record(
            action="caregiver.viewed_patient_data",
            actor_user_id=caregiver.id,
            target_user_id=patient.id,
            resource_type="patient",
            resource_id=patient.id,
            metadata={"view": "today"},
        )
        schedules = await ScheduleService(self.session).today(patient)
        dose_logs = await DoseLogService(self.session, self.settings).today(patient)
        return PatientTodayResponse(
            patient_id=patient.id,
            schedules=schedules,
            dose_logs=dose_logs,
        )

    async def dose_logs(self, caregiver: User, patient_id: UUID) -> list[DoseLog]:
        patient = await CaregiverAuthorizationService(self.session).resolve_patient(
            caregiver, patient_id
        )
        await self.audit.record(
            action="caregiver.viewed_patient_data",
            actor_user_id=caregiver.id,
            target_user_id=patient.id,
            resource_type="patient",
            resource_id=patient.id,
            metadata={"view": "dose_logs"},
        )
        await self.session.commit()
        return list(await DoseLogRepository(self.session).list_for_user(patient.id))

    async def revoke(self, patient: User, link_id: UUID) -> CaregiverLink:
        _require_role(patient, UserRole.PATIENT)
        link = await self.links.get_for_patient(link_id, patient.id)
        if link is None:
            raise AppError(
                code="caregiver_link_not_found",
                message="Caregiver link not found",
                status_code=404,
            )
        if link.status is CaregiverLinkStatus.REVOKED:
            return link
        await self.links.revoke(link)
        await self.audit.record(
            action="caregiver.revoked",
            actor_user_id=patient.id,
            target_user_id=patient.id,
            resource_type="caregiver_link",
            resource_id=link.id,
        )
        await self.session.commit()
        await self.session.refresh(link)
        return link


def _require_role(user: User, role: UserRole) -> None:
    if user.role is not role:
        raise authorization_error()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _is_link_conflict(exc: IntegrityError) -> bool:
    error_text = str(exc.orig).casefold()
    return "unique" in error_text and "caregiver_links" in error_text
