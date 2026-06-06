import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.caregiver import CaregiverLink
from app.tests.conftest import register_user


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def invite_and_accept(
    client: TestClient,
    *,
    patient_email: str = "patient@example.com",
    caregiver_email: str = "caregiver@example.com",
    permission: str = "VIEW_ONLY",
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    patient = register_user(client, email=patient_email)
    caregiver = register_user(client, email=caregiver_email, role="CAREGIVER")
    patient_headers = bearer(patient["access_token"])
    caregiver_headers = bearer(caregiver["access_token"])
    invite = client.post(
        "/api/v1/caregivers/invite",
        headers=patient_headers,
        json={
            "caregiver_email": caregiver_email,
            "relationship": "Family",
            "permission_level": permission,
        },
    )
    assert invite.status_code == 201
    assert invite.json()["invite_token"]
    accepted = client.post(
        "/api/v1/caregivers/accept",
        headers=caregiver_headers,
        json={"invite_token": invite.json()["invite_token"]},
    )
    assert accepted.status_code == 200
    payload: dict[str, Any] = accepted.json()
    return patient_headers, caregiver_headers, payload


def create_patient_medication(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(
        "/api/v1/medications",
        headers=headers,
        json={
            "name": "Patient medication",
            "form": "TABLET",
            "source": "MANUAL",
            "active": True,
        },
    )
    assert response.status_code == 201
    payload: dict[str, Any] = response.json()
    return payload


def test_patient_invites_caregiver_and_caregiver_sees_only_linked_patient(
    client: TestClient,
) -> None:
    patient_headers, caregiver_headers, link = invite_and_accept(client)
    unlinked = register_user(client, email="unlinked@example.com")
    linked_patient = client.get("/api/v1/auth/me", headers=patient_headers).json()
    unlinked_patient = client.get(
        "/api/v1/auth/me", headers=bearer(unlinked["access_token"])
    ).json()
    unlinked_medication = create_patient_medication(client, bearer(unlinked["access_token"]))

    patients = client.get("/api/v1/caregivers/patients", headers=caregiver_headers)
    linked_today = client.get(
        f"/api/v1/caregivers/patients/{linked_patient['id']}/today",
        headers=caregiver_headers,
    )
    unlinked_today = client.get(
        f"/api/v1/caregivers/patients/{unlinked_patient['id']}/today",
        headers=caregiver_headers,
    )
    unlinked_logs = client.get(
        f"/api/v1/caregivers/patients/{unlinked_patient['id']}/dose-logs",
        headers=caregiver_headers,
    )
    guessed_medication = client.post(
        "/api/v1/schedules",
        headers=caregiver_headers,
        json={
            "medication_id": unlinked_medication["id"],
            "frequency_type": "AS_NEEDED",
            "start_date": "2026-06-04",
        },
    )

    assert link["status"] == "ACTIVE"
    assert len(patients.json()) == 1
    assert patients.json()[0]["patient"]["id"] == linked_patient["id"]
    assert linked_today.status_code == 200
    assert unlinked_today.status_code == 403
    assert unlinked_logs.status_code == 403
    assert guessed_medication.status_code == 404


def test_view_only_can_read_schedules_and_dose_logs_but_cannot_manage(
    client: TestClient,
) -> None:
    patient_headers, caregiver_headers, _ = invite_and_accept(client)
    patient = client.get("/api/v1/auth/me", headers=patient_headers).json()
    medication = create_patient_medication(client, patient_headers)
    schedule = client.post(
        "/api/v1/schedules",
        headers=patient_headers,
        json={
            "medication_id": medication["id"],
            "frequency_type": "DAILY",
            "scheduled_time": "08:00:00",
            "start_date": "2026-06-04",
        },
    ).json()

    schedules = client.get(
        f"/api/v1/schedules?patient_id={patient['id']}", headers=caregiver_headers
    )
    dose_logs = client.get(
        f"/api/v1/caregivers/patients/{patient['id']}/dose-logs",
        headers=caregiver_headers,
    )
    medications = client.get(
        f"/api/v1/medications?patient_id={patient['id']}", headers=caregiver_headers
    )
    update_schedule = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=caregiver_headers,
        json={"active": False},
    )

    assert schedules.status_code == 200
    assert len(schedules.json()) == 1
    assert dose_logs.status_code == 200
    assert medications.status_code == 403
    assert update_schedule.status_code == 404


def test_manage_medications_permission_can_manage_medications_and_schedules(
    client: TestClient,
) -> None:
    patient_headers, caregiver_headers, _ = invite_and_accept(
        client, permission="MANAGE_MEDICATIONS"
    )
    patient = client.get("/api/v1/auth/me", headers=patient_headers).json()

    created = client.post(
        f"/api/v1/medications?patient_id={patient['id']}",
        headers=caregiver_headers,
        json={
            "name": "Caregiver entered medication",
            "form": "TABLET",
            "source": "CAREGIVER",
            "active": True,
        },
    )
    updated = client.patch(
        f"/api/v1/medications/{created.json()['id']}",
        headers=caregiver_headers,
        json={"brand_name": "User-visible brand"},
    )
    schedule = client.post(
        "/api/v1/schedules",
        headers=caregiver_headers,
        json={
            "medication_id": created.json()["id"],
            "frequency_type": "AS_NEEDED",
            "start_date": "2026-06-04",
        },
    )
    updated_schedule = client.patch(
        f"/api/v1/schedules/{schedule.json()['id']}",
        headers=caregiver_headers,
        json={"reminder_offset_minutes": 10},
    )

    assert created.status_code == 201
    assert created.json()["user_id"] == patient["id"]
    assert created.json()["source"] == "CAREGIVER"
    assert updated.status_code == 200
    assert schedule.status_code == 201
    assert updated_schedule.status_code == 200


def test_revoke_immediately_removes_caregiver_access(client: TestClient) -> None:
    patient_headers, caregiver_headers, link = invite_and_accept(client, permission="FULL_ACCESS")
    patient = client.get("/api/v1/auth/me", headers=patient_headers).json()
    inherited_management = client.get(
        f"/api/v1/medications?patient_id={patient['id']}", headers=caregiver_headers
    )

    revoked = client.patch(
        f"/api/v1/caregivers/links/{link['id']}/revoke",
        headers=patient_headers,
    )
    patients = client.get("/api/v1/caregivers/patients", headers=caregiver_headers)
    today = client.get(
        f"/api/v1/caregivers/patients/{patient['id']}/today",
        headers=caregiver_headers,
    )

    assert revoked.status_code == 200
    assert inherited_management.status_code == 200
    assert revoked.json()["status"] == "REVOKED"
    assert patients.json() == []
    assert today.status_code == 403


def test_invalid_and_expired_invites_fail(client: TestClient) -> None:
    patient = register_user(client)
    caregiver = register_user(client, email="caregiver@example.com", role="CAREGIVER")
    patient_headers = bearer(patient["access_token"])
    caregiver_headers = bearer(caregiver["access_token"])
    invite = client.post(
        "/api/v1/caregivers/invite",
        headers=patient_headers,
        json={
            "caregiver_email": "caregiver@example.com",
            "permission_level": "VIEW_ONLY",
        },
    ).json()
    app = client.app
    assert isinstance(app, FastAPI)

    async def expire_invite() -> None:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            await session.execute(
                update(CaregiverLink)
                .where(CaregiverLink.id == UUID(invite["id"]))
                .values(invite_expires_at=datetime.now(UTC) - timedelta(minutes=1))
            )
            await session.commit()

    asyncio.run(expire_invite())
    expired = client.post(
        "/api/v1/caregivers/accept",
        headers=caregiver_headers,
        json={"invite_token": invite["invite_token"]},
    )
    invalid = client.post(
        "/api/v1/caregivers/accept",
        headers=caregiver_headers,
        json={"invite_token": "x" * 43},
    )

    assert expired.status_code == 400
    assert expired.json()["error"]["code"] == "expired_invite"
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_invite"


def test_invite_cannot_be_accepted_by_different_caregiver(client: TestClient) -> None:
    patient = register_user(client)
    intended = register_user(client, email="intended@example.com", role="CAREGIVER")
    other = register_user(client, email="other@example.com", role="CAREGIVER")
    invite = client.post(
        "/api/v1/caregivers/invite",
        headers=bearer(patient["access_token"]),
        json={
            "caregiver_email": "intended@example.com",
            "permission_level": "VIEW_ONLY",
        },
    ).json()

    response = client.post(
        "/api/v1/caregivers/accept",
        headers=bearer(other["access_token"]),
        json={"invite_token": invite["invite_token"]},
    )

    assert intended["access_token"]
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_invite"


def test_invite_fails_safely_when_delivery_is_not_configured(client: TestClient) -> None:
    patient = register_user(client)
    app = client.app
    assert isinstance(app, FastAPI)
    app.state.settings.caregiver_invite_token_return_enabled = False

    response = client.post(
        "/api/v1/caregivers/invite",
        headers=bearer(patient["access_token"]),
        json={
            "caregiver_email": "caregiver@example.com",
            "permission_level": "VIEW_ONLY",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "notification_provider_unconfigured"
