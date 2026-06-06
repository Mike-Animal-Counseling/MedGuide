import asyncio
from datetime import UTC, datetime, timedelta
from io import StringIO
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import JsonFormatter
from app.core.redaction import REDACTED, redact_sensitive
from app.models.audit import AuditLog
from app.models.upload import UploadedImage
from app.services.retention import RetentionCleanupService
from app.tests.conftest import register_user
from app.tests.test_caregivers import invite_and_accept
from app.tests.test_schedules import bearer, create_daily_schedule
from app.tests.test_uploads import create_image, storage_for


def audit_actions(client: TestClient) -> list[str]:
    app = client.app
    assert isinstance(app, FastAPI)

    async def load() -> list[str]:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            result = await session.scalars(select(AuditLog.action).order_by(AuditLog.created_at))
            return list(result)

    return asyncio.run(load())


def test_audit_logs_created_for_critical_user_medication_schedule_and_dose_actions(
    client: TestClient,
) -> None:
    tokens = register_user(client, email="audit-patient@example.com")
    headers = bearer(tokens["access_token"])
    medication = client.post(
        "/api/v1/medications",
        headers=headers,
        json={"name": "Audit medication", "form": "TABLET", "source": "MANUAL"},
    ).json()
    updated_med = client.patch(
        f"/api/v1/medications/{medication['id']}",
        headers=headers,
        json={"brand_name": "Brand"},
    )
    schedule = create_daily_schedule(client, headers, medication["id"])
    updated_schedule = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=headers,
        json={"reminder_offset_minutes": 5},
    )
    dose = client.get("/api/v1/dose-logs/today", headers=headers).json()[0]
    confirmed = client.patch(
        f"/api/v1/dose-logs/{dose['id']}/confirm",
        headers=headers,
        json={"confirmation_method": "BUTTON", "actual_taken_time": dose["scheduled_time"]},
    )
    deleted_schedule = client.delete(f"/api/v1/schedules/{schedule['id']}", headers=headers)
    deleted_med = client.delete(f"/api/v1/medications/{medication['id']}", headers=headers)

    actions = set(audit_actions(client))

    assert updated_med.status_code == 200
    assert updated_schedule.status_code == 200
    assert confirmed.status_code == 200
    assert deleted_schedule.status_code == 204
    assert deleted_med.status_code == 204
    assert {
        "user.registered",
        "medication.created",
        "medication.updated",
        "medication.deleted",
        "schedule.created",
        "schedule.updated",
        "schedule.deleted",
        "dose.confirmed",
    } <= actions


def test_privacy_export_returns_own_data_without_sensitive_fields(client: TestClient) -> None:
    storage_for(client)
    owner = bearer(register_user(client, email="privacy-owner@example.com")["access_token"])
    other = bearer(register_user(client, email="privacy-other@example.com")["access_token"])
    owner_image = create_image(client, owner)
    other_image = create_image(client, other)

    response = client.get("/api/v1/privacy/export", headers=owner)
    unauthorized = client.get("/api/v1/privacy/export")

    image_ids = {item["id"] for item in response.json()["images"]}
    text = str(response.json()).casefold()
    assert response.status_code == 200
    assert owner_image["image_id"] in image_ids
    assert other_image["image_id"] not in image_ids
    assert unauthorized.status_code == 401
    assert "password_hash" not in text
    assert "push_token" not in text
    assert "object_key" not in text
    assert "read_url" not in text


def test_privacy_image_delete_denies_signed_read_after_delete(client: TestClient) -> None:
    storage = storage_for(client)
    headers = bearer(register_user(client, email="privacy-image@example.com")["access_token"])
    image = create_image(client, headers)

    deleted = client.delete(f"/api/v1/privacy/images/{image['image_id']}", headers=headers)
    read = client.get(f"/api/v1/uploads/{image['image_id']}/signed-read-url", headers=headers)

    assert deleted.status_code == 204
    assert read.status_code == 404
    assert len(storage.deletes) == 1
    assert "image.deleted" in audit_actions(client)


def test_privacy_revoke_caregiver_removes_access(client: TestClient) -> None:
    patient_headers, caregiver_headers, link = invite_and_accept(
        client,
        patient_email="privacy-revoke-patient@example.com",
        caregiver_email="privacy-revoke-caregiver@example.com",
    )
    patient = client.get("/api/v1/auth/me", headers=patient_headers).json()

    revoked = client.post(
        f"/api/v1/privacy/revoke-caregiver/{link['id']}",
        headers=patient_headers,
    )
    today = client.get(
        f"/api/v1/caregivers/patients/{patient['id']}/today",
        headers=caregiver_headers,
    )

    assert revoked.status_code == 204
    assert today.status_code == 403
    assert "caregiver.revoked" in audit_actions(client)


def test_redaction_utility_and_json_formatter_remove_sensitive_values() -> None:
    payload = redact_sensitive(
        {
            "authorization": "Bearer secret.jwt.token",
            "nested": {"ocr_text": "raw label text", "safe": "ok"},
            "items": [{"push_token": "ExpoPushToken[secret]"}],
        }
    )
    stream = StringIO()
    import logging

    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "message",
        args=(),
        exc_info=None,
    )
    record.access_token = "secret-token"
    handler.handle(record)

    assert payload["authorization"] == REDACTED
    assert payload["nested"]["ocr_text"] == REDACTED
    assert payload["items"][0]["push_token"] == REDACTED
    assert "secret-token" not in stream.getvalue()
    assert REDACTED in stream.getvalue()


def test_retention_cleanup_deletes_only_when_configured(client: TestClient) -> None:
    storage = storage_for(client)
    headers = bearer(register_user(client, email="retention@example.com")["access_token"])
    image = create_image(client, headers)
    app = client.app
    assert isinstance(app, FastAPI)

    async def age_image() -> int:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            await session.execute(
                update(UploadedImage)
                .where(UploadedImage.id == UUID(image["image_id"]))
                .values(created_at=datetime.now(UTC) - timedelta(days=2))
            )
            await session.commit()
            app.state.settings.storage_retention_days = None
            skipped = await RetentionCleanupService(
                session, app.state.settings, storage
            ).cleanup_expired_images()
            app.state.settings.storage_retention_days = 1
            return (
                skipped
                + await RetentionCleanupService(
                    session, app.state.settings, storage
                ).cleanup_expired_images()
            )

    deleted_count = asyncio.run(age_image())
    read = client.get(f"/api/v1/uploads/{image['image_id']}/signed-read-url", headers=headers)

    assert deleted_count == 1
    assert read.status_code == 404
    assert len(storage.deletes) == 1
