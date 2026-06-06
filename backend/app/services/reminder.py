from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.observability import InMemoryMetricsService, MetricsService, record_event
from app.models.notification import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
    NotificationType,
)
from app.models.schedule import ConfirmationMethod, DoseLog, DoseStatus
from app.repositories.caregiver import CaregiverLinkRepository
from app.repositories.notification import NotificationEventRepository, UserDeviceRepository
from app.repositories.schedule import DoseLogRepository, ScheduleRepository
from app.repositories.user import UserRepository
from app.services.audit import AuditService
from app.services.push_notification import NotificationProvider, PushMessage
from app.services.schedule_engine import generate_scheduled_times


class ReminderProcessor:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        provider: NotificationProvider,
        metrics: MetricsService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider
        self.metrics = metrics or InMemoryMetricsService()
        self.dose_logs = DoseLogRepository(session)
        self.events = NotificationEventRepository(session)
        self.devices = UserDeviceRepository(session)
        self.links = CaregiverLinkRepository(session)
        self.schedules = ScheduleRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)
        self.processed_event_ids: set[UUID] = set()

    async def process_reminders(self, now: datetime | None = None) -> None:
        current = _as_utc(now or datetime.now(UTC))
        await self._ensure_current_doses(current)
        await self._retry_failed({NotificationType.DOSE_REMINDER, NotificationType.SNOOZE_REMINDER})
        for dose in await self.dose_logs.list_pending_before(current):
            await self._deliver(
                dose=dose,
                recipient_id=dose.user_id,
                caregiver_id=None,
                notification_type=NotificationType.DOSE_REMINDER,
            )
            if current >= _as_utc(dose.scheduled_time) + timedelta(
                minutes=self.settings.reminder_second_offset_minutes
            ):
                await self._deliver(
                    dose=dose,
                    recipient_id=dose.user_id,
                    caregiver_id=None,
                    notification_type=NotificationType.SNOOZE_REMINDER,
                )

    async def process_escalations(self, now: datetime | None = None) -> None:
        current = _as_utc(now or datetime.now(UTC))
        await self._ensure_current_doses(current)
        await self._retry_failed(
            {NotificationType.CAREGIVER_ESCALATION, NotificationType.MISSED_DOSE_ALERT}
        )
        for dose in await self.dose_logs.list_pending_before(current):
            scheduled = _as_utc(dose.scheduled_time)
            links = await self.links.list_active_for_patient(dose.user_id)
            if current >= scheduled + timedelta(minutes=self.settings.reminder_escalation_minutes):
                for link in links:
                    if link.caregiver_id is not None:
                        await self._deliver(
                            dose=dose,
                            recipient_id=link.caregiver_id,
                            caregiver_id=link.caregiver_id,
                            notification_type=NotificationType.CAREGIVER_ESCALATION,
                        )
            if current >= scheduled + timedelta(
                minutes=self.settings.reminder_missed_cutoff_minutes
            ):
                dose.status = DoseStatus.MISSED
                dose.confirmation_method = ConfirmationMethod.AUTO_MISSED
                await self.audit.record(
                    action="dose.missed",
                    actor_user_id=None,
                    target_user_id=dose.user_id,
                    resource_type="dose_log",
                    resource_id=dose.id,
                    metadata={"status": DoseStatus.MISSED.value},
                )
                record_event(
                    self.metrics,
                    "dose_missed",
                    metadata={"dose_log_id": str(dose.id), "user_id": str(dose.user_id)},
                )
                await self.session.commit()
                for link in links:
                    if link.caregiver_id is not None:
                        await self._deliver(
                            dose=dose,
                            recipient_id=link.caregiver_id,
                            caregiver_id=link.caregiver_id,
                            notification_type=NotificationType.MISSED_DOSE_ALERT,
                        )

    async def _deliver(
        self,
        *,
        dose: DoseLog,
        recipient_id: UUID,
        caregiver_id: UUID | None,
        notification_type: NotificationType,
    ) -> None:
        event = await self.events.get_for_delivery(
            dose_log_id=dose.id,
            notification_type=notification_type,
            channel=NotificationChannel.PUSH,
            caregiver_id=caregiver_id,
        )
        if event is not None and event.status is NotificationStatus.SENT:
            return
        if event is not None and event.id in self.processed_event_ids:
            return
        attempts = _attempts(event)
        if event is not None and attempts >= self.settings.notification_retry_max_attempts:
            return
        if event is None:
            event = await self.events.add(
                NotificationEvent(
                    user_id=dose.user_id,
                    caregiver_id=caregiver_id,
                    dose_log_id=dose.id,
                    notification_type=notification_type,
                    channel=NotificationChannel.PUSH,
                    status=NotificationStatus.PENDING,
                    provider_response={"attempts": 0},
                )
            )
        elif attempts:
            event.status = NotificationStatus.RETRYING
        self.processed_event_ids.add(event.id)
        await self.session.commit()

        tokens = await self.devices.list_active_tokens(recipient_id)
        try:
            delivery = await self.provider.send_push(
                push_tokens=tokens,
                message=_message(notification_type, dose.id),
            )
        except AppError as exc:
            event.status = NotificationStatus.FAILED
            event.error_message = exc.message
            event.provider_response = {"attempts": attempts + 1, "error_code": exc.code}
            await self.audit.record(
                action="notification.failed",
                actor_user_id=None,
                target_user_id=event.caregiver_id or event.user_id,
                resource_type="notification_event",
                resource_id=event.id,
                metadata={
                    "notification_type": event.notification_type.value,
                    "channel": event.channel.value,
                    "error_code": exc.code,
                },
            )
            record_event(
                self.metrics,
                "notification_failed",
                tags={"notification_type": event.notification_type.value},
                metadata={"notification_event_id": str(event.id), "error_code": exc.code},
            )
            await self.session.commit()
            return
        if not delivery.accepted:
            event.status = NotificationStatus.FAILED
            event.error_message = "Push notification provider rejected the delivery"
            event.provider_response = {
                "attempts": attempts + 1,
                "provider": delivery.response,
            }
            await self.audit.record(
                action="notification.failed",
                actor_user_id=None,
                target_user_id=event.caregiver_id or event.user_id,
                resource_type="notification_event",
                resource_id=event.id,
                metadata={
                    "notification_type": event.notification_type.value,
                    "channel": event.channel.value,
                },
            )
            record_event(
                self.metrics,
                "notification_failed",
                tags={"notification_type": event.notification_type.value},
                metadata={"notification_event_id": str(event.id)},
            )
            await self.session.commit()
            return
        event.status = NotificationStatus.SENT
        event.error_message = None
        event.provider_response = {"attempts": attempts + 1, "provider": delivery.response}
        event.sent_at = datetime.now(UTC)
        await self.audit.record(
            action="notification.sent",
            actor_user_id=None,
            target_user_id=event.caregiver_id or event.user_id,
            resource_type="notification_event",
            resource_id=event.id,
            metadata={
                "notification_type": event.notification_type.value,
                "channel": event.channel.value,
            },
        )
        if event.notification_type is NotificationType.CAREGIVER_ESCALATION:
            record_event(
                self.metrics,
                "caregiver_escalation_sent",
                metadata={"notification_event_id": str(event.id), "dose_log_id": str(dose.id)},
            )
        else:
            record_event(
                self.metrics,
                "reminder_sent",
                tags={"notification_type": event.notification_type.value},
                metadata={"notification_event_id": str(event.id), "dose_log_id": str(dose.id)},
            )
        await self.session.commit()

    async def _retry_failed(self, notification_types: set[NotificationType]) -> None:
        for event in await self.events.list_failed_for_types(notification_types):
            if event.dose_log_id is None:
                continue
            dose = await self.dose_logs.get_record(event.dose_log_id)
            if dose is None:
                continue
            await self._deliver(
                dose=dose,
                recipient_id=event.caregiver_id or event.user_id,
                caregiver_id=event.caregiver_id,
                notification_type=event.notification_type,
            )

    async def _ensure_current_doses(self, current: datetime) -> None:
        for patient in await self.users.list_active_patients():
            timezone = ZoneInfo(patient.timezone)
            local_date = current.astimezone(timezone).date()
            for schedule in await self.schedules.list_active_for_range(
                patient.id, local_date, local_date
            ):
                await self.dose_logs.insert_pending_idempotently(
                    user_id=patient.id,
                    medication_id=schedule.medication_id,
                    schedule_id=schedule.id,
                    scheduled_times=generate_scheduled_times(
                        schedule,
                        range_start=local_date,
                        range_end=local_date,
                        timezone=timezone,
                    ),
                )
        await self.session.commit()


def _message(notification_type: NotificationType, dose_log_id: UUID) -> PushMessage:
    content = {
        NotificationType.DOSE_REMINDER: (
            "Medication reminder",
            "A scheduled medication is due. Please check your confirmed medication details.",
        ),
        NotificationType.SNOOZE_REMINDER: (
            "Medication reminder",
            "A scheduled medication is still awaiting confirmation.",
        ),
        NotificationType.CAREGIVER_ESCALATION: (
            "Caregiver check requested",
            "A linked patient has not confirmed a scheduled medication.",
        ),
        NotificationType.MISSED_DOSE_ALERT: (
            "Missed medication update",
            "A linked patient's scheduled medication was marked missed.",
        ),
        NotificationType.DAILY_SUMMARY: (
            "Medication summary",
            "A medication assistance summary is available.",
        ),
    }
    title, body = content[notification_type]
    return PushMessage(title=title, body=body, data={"dose_log_id": str(dose_log_id)})


def _attempts(event: NotificationEvent | None) -> int:
    if event is None or event.provider_response is None:
        return 0
    value: Any = event.provider_response.get("attempts", 0)
    return int(value) if isinstance(value, int | float) else 0


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
