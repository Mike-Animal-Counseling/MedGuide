import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.models.notification import NotificationEvent, NotificationStatus, NotificationType
from app.models.schedule import DoseLog, DoseStatus
from app.services.push_notification import ProviderDeliveryResult, PushMessage
from app.services.reminder import ReminderProcessor
from app.tests.test_caregivers import invite_and_accept
from app.tests.test_schedules import setup_schedule


class RecordingNotificationProvider:
    def __init__(self, *, failures: int = 0) -> None:
        self.failures = failures
        self.messages: list[tuple[list[str], PushMessage]] = []

    async def send_push(
        self, *, push_tokens: list[str], message: PushMessage
    ) -> ProviderDeliveryResult:
        self.messages.append((push_tokens, message))
        if not push_tokens:
            self.messages.pop()
            raise AppError(
                code="notification_recipient_unavailable",
                message="No active push device is registered",
                status_code=409,
            )
        if len(self.messages) <= self.failures:
            raise AppError(
                code="notification_provider_unavailable",
                message="Push notification provider is temporarily unavailable",
                status_code=503,
            )
        return ProviderDeliveryResult(response={"data": [{"status": "ok"}]})


def register_device(client: TestClient, headers: dict[str, str], suffix: str) -> None:
    response = client.post(
        "/api/v1/devices",
        headers=headers,
        json={"platform": "IOS", "push_token": f"ExpoPushToken[{suffix}]"},
    )
    assert response.status_code == 201


def due_dose(
    client: TestClient,
    *,
    headers: dict[str, str] | None = None,
    minutes_ago: int = 0,
) -> tuple[dict[str, str], dict[str, Any]]:
    scheduled_time = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).replace(microsecond=0)
    if headers is None:
        headers, _, schedule = setup_schedule(client, "reminder-patient@example.com")
    else:
        medication = client.post(
            "/api/v1/medications",
            headers=headers,
            json={
                "name": "Confirmed reminder medication",
                "form": "TABLET",
                "source": "MANUAL",
                "active": True,
            },
        ).json()
        from app.tests.test_schedules import create_daily_schedule

        schedule = create_daily_schedule(client, headers, medication["id"])
    local_scheduled_time = (
        scheduled_time.astimezone(ZoneInfo("America/Chicago"))
        .time()
        .replace(tzinfo=None)
        .isoformat()
    )
    updated = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=headers,
        json={"scheduled_time": local_scheduled_time},
    )
    assert updated.status_code == 200
    dose = client.get("/api/v1/dose-logs/today", headers=headers).json()[0]
    set_dose_scheduled_time(client, dose["id"], scheduled_time)
    return headers, dose


def run_processor(
    client: TestClient,
    provider: RecordingNotificationProvider,
    operation: str,
) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    async def run() -> None:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            processor = ReminderProcessor(session, app.state.settings, provider)
            await getattr(processor, operation)(datetime.now(UTC))

    asyncio.run(run())


def load_events(client: TestClient, dose_log_id: str) -> list[NotificationEvent]:
    app = client.app
    assert isinstance(app, FastAPI)

    async def load() -> list[NotificationEvent]:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            result = await session.scalars(
                select(NotificationEvent).where(NotificationEvent.dose_log_id == UUID(dose_log_id))
            )
            return list(result)

    return asyncio.run(load())


def load_dose_status(client: TestClient, dose_log_id: str) -> DoseStatus:
    app = client.app
    assert isinstance(app, FastAPI)

    async def load() -> DoseStatus:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            status = await session.scalar(
                select(DoseLog.status).where(DoseLog.id == UUID(dose_log_id))
            )
            assert status is not None
            return status

    return asyncio.run(load())


def set_dose_scheduled_time(client: TestClient, dose_log_id: str, scheduled_time: datetime) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    async def update() -> None:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            dose = await session.get(DoseLog, UUID(dose_log_id))
            assert dose is not None
            dose.scheduled_time = scheduled_time
            await session.commit()

    asyncio.run(update())


def test_push_reminder_sent_and_duplicate_job_is_idempotent(client: TestClient) -> None:
    headers, dose = due_dose(client)
    register_device(client, headers, "patient-reminder-token")
    provider = RecordingNotificationProvider()

    run_processor(client, provider, "process_reminders")
    run_processor(client, provider, "process_reminders")
    events = load_events(client, dose["id"])

    assert len(provider.messages) == 1
    assert len(events) == 1
    assert events[0].notification_type is NotificationType.DOSE_REMINDER
    assert events[0].status is NotificationStatus.SENT
    assert events[0].sent_at is not None


def test_worker_generates_current_dose_without_patient_opening_today_endpoint(
    client: TestClient,
) -> None:
    headers, _, schedule = setup_schedule(client, "background-generation@example.com")
    target = datetime.now(UTC) - timedelta(minutes=1)
    local_time = target.astimezone(ZoneInfo("America/Chicago")).time().replace(tzinfo=None)
    updated = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=headers,
        json={"scheduled_time": local_time.isoformat()},
    )
    assert updated.status_code == 200
    register_device(client, headers, "background-generation-token")
    provider = RecordingNotificationProvider()

    run_processor(client, provider, "process_reminders")
    generated = client.get("/api/v1/dose-logs", headers=headers)

    assert len(generated.json()) == 1
    assert len(provider.messages) == 1


def test_second_reminder_is_sent_once_after_configured_offset(client: TestClient) -> None:
    headers, dose = due_dose(client, minutes_ago=16)
    register_device(client, headers, "second-reminder-token")
    provider = RecordingNotificationProvider()

    run_processor(client, provider, "process_reminders")
    run_processor(client, provider, "process_reminders")
    events = load_events(client, dose["id"])

    assert len(provider.messages) == 2
    assert {event.notification_type for event in events} == {
        NotificationType.DOSE_REMINDER,
        NotificationType.SNOOZE_REMINDER,
    }


def test_failed_notification_retries_and_updates_status(client: TestClient) -> None:
    headers, dose = due_dose(client)
    register_device(client, headers, "retry-token")
    provider = RecordingNotificationProvider(failures=1)

    run_processor(client, provider, "process_reminders")
    failed = load_events(client, dose["id"])[0]
    assert failed.status is NotificationStatus.FAILED
    assert failed.error_message

    run_processor(client, provider, "process_reminders")
    sent = load_events(client, dose["id"])[0]

    assert len(provider.messages) == 2
    assert sent.status is NotificationStatus.SENT
    assert sent.provider_response is not None
    assert sent.provider_response["attempts"] == 2


def test_escalation_notifies_active_caregiver(client: TestClient) -> None:
    patient_headers, caregiver_headers, _ = invite_and_accept(
        client,
        patient_email="escalation-patient@example.com",
        caregiver_email="escalation-caregiver@example.com",
    )
    _, dose = due_dose(client, headers=patient_headers, minutes_ago=31)
    register_device(client, caregiver_headers, "caregiver-escalation-token")
    provider = RecordingNotificationProvider()

    run_processor(client, provider, "process_escalations")
    events = load_events(client, dose["id"])

    assert len(provider.messages) == 1
    assert events[0].notification_type is NotificationType.CAREGIVER_ESCALATION
    assert events[0].caregiver_id is not None
    assert events[0].status is NotificationStatus.SENT


def test_cutoff_marks_pending_dose_missed(client: TestClient) -> None:
    headers, dose = due_dose(client, minutes_ago=61)
    assert headers
    provider = RecordingNotificationProvider()

    run_processor(client, provider, "process_escalations")
    run_processor(client, provider, "process_escalations")

    assert load_dose_status(client, dose["id"]) is DoseStatus.MISSED
    assert provider.messages == []


def test_failed_caregiver_alert_retries_after_dose_is_marked_missed(
    client: TestClient,
) -> None:
    patient_headers, caregiver_headers, _ = invite_and_accept(
        client,
        patient_email="missed-retry-patient@example.com",
        caregiver_email="missed-retry-caregiver@example.com",
    )
    _, dose = due_dose(client, headers=patient_headers, minutes_ago=61)
    register_device(client, caregiver_headers, "missed-retry-token")
    provider = RecordingNotificationProvider(failures=2)

    run_processor(client, provider, "process_escalations")
    assert load_dose_status(client, dose["id"]) is DoseStatus.MISSED
    assert {event.status for event in load_events(client, dose["id"])} == {
        NotificationStatus.FAILED
    }

    run_processor(client, provider, "process_escalations")
    events = load_events(client, dose["id"])

    assert len(provider.messages) == 4
    assert {event.status for event in events} == {NotificationStatus.SENT}


def test_missing_device_records_failed_event_without_fake_send(client: TestClient) -> None:
    _, dose = due_dose(client)
    provider = RecordingNotificationProvider()

    run_processor(client, provider, "process_reminders")
    event = load_events(client, dose["id"])[0]

    assert event.status is NotificationStatus.FAILED
    assert event.provider_response is not None
    assert event.provider_response["error_code"] == "notification_recipient_unavailable"
