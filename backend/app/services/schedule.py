from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.observability import MetricsService, NullMetricsService, record_event
from app.models.caregiver import CaregiverPermission
from app.models.schedule import (
    ConfirmationMethod,
    DoseLog,
    DoseStatus,
    FrequencyType,
    MedicationSchedule,
)
from app.models.user import User, UserRole
from app.repositories.medication import MedicationRepository
from app.repositories.schedule import DoseLogRepository, ScheduleRepository
from app.schemas.schedule import (
    DoseConfirmRequest,
    DoseStatusRequest,
    ScheduleCreateRequest,
    ScheduleFields,
    ScheduleUpdateRequest,
)
from app.services.audit import AuditService, NullAuditService
from app.services.caregiver_authorization import CaregiverAuthorizationService
from app.services.schedule_engine import generate_scheduled_times, local_day_bounds


class ScheduleService:
    def __init__(
        self, session: AsyncSession, audit: AuditService | NullAuditService | None = None
    ) -> None:
        self.session = session
        self.audit = audit or NullAuditService()
        self.schedules = ScheduleRepository(session)
        self.medications = MedicationRepository(session)
        self.authorization = CaregiverAuthorizationService(session)

    async def create(self, user: User, request: ScheduleCreateRequest) -> MedicationSchedule:
        medication = await self.medications.get_active_record(request.medication_id)
        if medication is None:
            raise _not_found("medication_not_found", "Medication not found")
        try:
            patient = await self.authorization.resolve_patient(
                user,
                medication.user_id,
                required_permission=CaregiverPermission.MANAGE_MEDICATIONS,
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found("medication_not_found", "Medication not found") from exc
            raise
        if request.active and not medication.active:
            raise AppError(
                code="inactive_medication",
                message="Inactive medication cannot have an active schedule",
                status_code=409,
            )
        schedule = await self.schedules.add(
            MedicationSchedule(user_id=patient.id, created_by=user.id, **request.model_dump())
        )
        await self.audit.record(
            action="schedule.created",
            actor_user_id=user.id,
            target_user_id=patient.id,
            resource_type="schedule",
            resource_id=schedule.id,
            metadata={"frequency_type": schedule.frequency_type.value},
        )
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def list_for_user(
        self, user: User, patient_id: UUID | None = None
    ) -> list[MedicationSchedule]:
        patient = await self.authorization.resolve_patient(user, patient_id)
        return await self.schedules.list_for_user(patient.id)

    async def today(
        self, user: User, today: date | None = None, patient_id: UUID | None = None
    ) -> list[MedicationSchedule]:
        patient = await self.authorization.resolve_patient(user, patient_id)
        target_date = today or datetime.now(ZoneInfo(patient.timezone)).date()
        schedules = await self.schedules.list_active_for_range(patient.id, target_date, target_date)
        return [
            schedule
            for schedule in schedules
            if generate_scheduled_times(
                schedule,
                range_start=target_date,
                range_end=target_date,
                timezone=ZoneInfo(patient.timezone),
            )
            or schedule.frequency_type is FrequencyType.AS_NEEDED
        ]

    async def update(
        self, user: User, schedule_id: UUID, request: ScheduleUpdateRequest
    ) -> MedicationSchedule:
        schedule = await self._get(user, schedule_id)
        changes = request.model_dump(exclude_unset=True)
        candidate_data = {
            "medication_id": schedule.medication_id,
            "frequency_type": schedule.frequency_type,
            "scheduled_time": schedule.scheduled_time,
            "days_of_week": schedule.days_of_week,
            "interval_hours": schedule.interval_hours,
            "start_date": schedule.start_date,
            "end_date": schedule.end_date,
            "reminder_offset_minutes": schedule.reminder_offset_minutes,
            "active": schedule.active,
            **changes,
        }
        validated = ScheduleFields.model_validate(candidate_data)
        if validated.active:
            medication = await self.medications.get_for_user(
                schedule.medication_id, schedule.user_id
            )
            if medication is None:
                raise _not_found("medication_not_found", "Medication not found")
            if not medication.active:
                raise AppError(
                    code="inactive_medication",
                    message="Inactive medication cannot have an active schedule",
                    status_code=409,
                )
        for field, value in validated.model_dump(exclude={"medication_id"}).items():
            setattr(schedule, field, value)
        await self.audit.record(
            action="schedule.updated",
            actor_user_id=user.id,
            target_user_id=schedule.user_id,
            resource_type="schedule",
            resource_id=schedule.id,
            metadata={"fields": sorted(changes)},
        )
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def delete(self, user: User, schedule_id: UUID) -> None:
        schedule = await self._get(user, schedule_id)
        schedule.active = False
        await self.audit.record(
            action="schedule.deleted",
            actor_user_id=user.id,
            target_user_id=schedule.user_id,
            resource_type="schedule",
            resource_id=schedule.id,
        )
        await self.session.commit()

    async def _get(self, user: User, schedule_id: UUID) -> MedicationSchedule:
        schedule = await self.schedules.get_record(schedule_id)
        if schedule is None:
            raise _not_found("schedule_not_found", "Schedule not found")
        try:
            await self.authorization.resolve_patient(
                user,
                schedule.user_id,
                required_permission=CaregiverPermission.MANAGE_MEDICATIONS,
            )
        except AppError as exc:
            if exc.status_code == 403:
                raise _not_found("schedule_not_found", "Schedule not found") from exc
            raise
        return schedule


class DoseLogService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        audit: AuditService | NullAuditService | None = None,
        metrics: MetricsService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.audit = audit or NullAuditService()
        self.metrics = metrics or NullMetricsService()
        self.schedules = ScheduleRepository(session)
        self.dose_logs = DoseLogRepository(session)

    async def generate_range(self, user: User, start_date: date, end_date: date) -> list[DoseLog]:
        _require_patient(user)
        if end_date < start_date:
            raise AppError(
                code="invalid_date_range",
                message="End date must be on or after start date",
                status_code=422,
            )
        timezone = ZoneInfo(user.timezone)
        schedules = await self.schedules.list_active_for_range(user.id, start_date, end_date)
        for schedule in schedules:
            await self.dose_logs.insert_pending_idempotently(
                user_id=user.id,
                medication_id=schedule.medication_id,
                schedule_id=schedule.id,
                scheduled_times=generate_scheduled_times(
                    schedule,
                    range_start=start_date,
                    range_end=end_date,
                    timezone=timezone,
                ),
            )
        await self.session.commit()
        start, _ = local_day_bounds(start_date, timezone)
        _, end = local_day_bounds(end_date, timezone)
        return await self.dose_logs.list_for_user(user.id, start=start, end=end)

    async def list_for_user(self, user: User) -> list[DoseLog]:
        _require_patient(user)
        return await self.dose_logs.list_for_user(user.id)

    async def today(self, user: User) -> list[DoseLog]:
        today = datetime.now(ZoneInfo(user.timezone)).date()
        return await self.generate_range(user, today, today)

    async def confirm(self, user: User, dose_log_id: UUID, request: DoseConfirmRequest) -> DoseLog:
        dose_log = await self._pending(user, dose_log_id)
        if request.confirmation_method in {
            ConfirmationMethod.CAREGIVER,
            ConfirmationMethod.AUTO_MISSED,
        }:
            raise AppError(
                code="invalid_confirmation_method",
                message="Confirmation method is not available for patient confirmation",
                status_code=422,
            )
        actual_time = request.actual_taken_time or datetime.now(UTC)
        if actual_time.tzinfo is None:
            raise AppError(
                code="invalid_actual_taken_time",
                message="actual_taken_time must include a timezone",
                status_code=422,
            )
        scheduled_time = dose_log.scheduled_time
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=UTC)
        window = timedelta(minutes=self.settings.dose_on_time_window_minutes)
        if actual_time < scheduled_time - window:
            dose_log.status = DoseStatus.VERIFICATION_FAILED
        elif actual_time <= scheduled_time + window:
            dose_log.status = DoseStatus.TAKEN_ON_TIME
        else:
            dose_log.status = DoseStatus.TAKEN_LATE
        dose_log.actual_taken_time = actual_time
        dose_log.confirmation_method = request.confirmation_method
        dose_log.notes = request.notes
        await self.audit.record(
            action="dose.confirmed",
            actor_user_id=user.id,
            target_user_id=dose_log.user_id,
            resource_type="dose_log",
            resource_id=dose_log.id,
            metadata={"status": dose_log.status.value, "method": request.confirmation_method.value},
        )
        record_event(
            self.metrics,
            "dose_confirmed",
            tags={"status": dose_log.status.value, "method": request.confirmation_method.value},
            metadata={"dose_log_id": str(dose_log.id), "user_id": str(dose_log.user_id)},
        )
        await self.session.commit()
        await self.session.refresh(dose_log)
        return dose_log

    async def skip(self, user: User, dose_log_id: UUID, request: DoseStatusRequest) -> DoseLog:
        return await self._set_status(user, dose_log_id, DoseStatus.SKIPPED, request.notes)

    async def needs_help(
        self, user: User, dose_log_id: UUID, request: DoseStatusRequest
    ) -> DoseLog:
        return await self._set_status(user, dose_log_id, DoseStatus.NEEDS_HELP, request.notes)

    async def _set_status(
        self, user: User, dose_log_id: UUID, status: DoseStatus, notes: str | None
    ) -> DoseLog:
        dose_log = await self._pending(user, dose_log_id)
        dose_log.status = status
        dose_log.notes = notes
        await self.audit.record(
            action="dose.skipped" if status is DoseStatus.SKIPPED else "dose.needs_help",
            actor_user_id=user.id,
            target_user_id=dose_log.user_id,
            resource_type="dose_log",
            resource_id=dose_log.id,
            metadata={"status": status.value},
        )
        await self.session.commit()
        await self.session.refresh(dose_log)
        return dose_log

    async def _pending(self, user: User, dose_log_id: UUID) -> DoseLog:
        _require_patient(user)
        dose_log = await self.dose_logs.get_for_user(dose_log_id, user.id)
        if dose_log is None:
            raise _not_found("dose_log_not_found", "Dose log not found")
        if dose_log.status is not DoseStatus.PENDING:
            raise AppError(
                code="dose_log_already_resolved",
                message="Dose log has already been resolved",
                status_code=409,
            )
        return dose_log


def _require_patient(user: User) -> None:
    if user.role is not UserRole.PATIENT:
        raise AppError(
            code="forbidden",
            message="Schedule access currently requires the patient account that owns the record",
            status_code=403,
        )


def _not_found(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=404)
