from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.tests.conftest import register_user


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def medication_payload() -> dict[str, Any]:
    return {
        "name": "User confirmed medication",
        "form": "TABLET",
        "instructions": "User-confirmed label text",
        "source": "MANUAL",
        "active": True,
    }


def create_medication(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post("/api/v1/medications", headers=headers, json=medication_payload())
    assert response.status_code == 201
    payload: dict[str, Any] = response.json()
    return payload


def create_daily_schedule(
    client: TestClient, headers: dict[str, str], medication_id: str
) -> dict[str, Any]:
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    response = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "medication_id": medication_id,
            "frequency_type": "DAILY",
            "scheduled_time": "08:00:00",
            "start_date": today,
        },
    )
    assert response.status_code == 201
    payload: dict[str, Any] = response.json()
    return payload


def setup_schedule(
    client: TestClient, email: str = "patient@example.com"
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    tokens = register_user(client, email=email)
    headers = bearer(tokens["access_token"])
    medication = create_medication(client, headers)
    schedule = create_daily_schedule(client, headers, medication["id"])
    return headers, medication, schedule


def test_schedule_crud_validation_and_authorization(client: TestClient) -> None:
    owner_headers, medication, schedule = setup_schedule(client, "owner@example.com")
    other_headers = bearer(register_user(client, email="other@example.com")["access_token"])

    listed = client.get("/api/v1/schedules", headers=owner_headers)
    updated = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=owner_headers,
        json={"reminder_offset_minutes": 15},
    )
    unauthorized = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=other_headers,
        json={"active": False},
    )
    invalid = client.post(
        "/api/v1/schedules",
        headers=owner_headers,
        json={
            "medication_id": medication["id"],
            "frequency_type": "WEEKLY",
            "scheduled_time": "08:00:00",
            "start_date": schedule["start_date"],
        },
    )

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert updated.json()["reminder_offset_minutes"] == 15
    assert unauthorized.status_code == 404
    assert invalid.status_code == 422


def test_today_generation_is_idempotent_and_preserves_history(client: TestClient) -> None:
    headers, _, schedule = setup_schedule(client)

    first = client.get("/api/v1/dose-logs/today", headers=headers)
    second = client.get("/api/v1/dose-logs/today", headers=headers)
    changed = client.patch(
        f"/api/v1/schedules/{schedule['id']}",
        headers=headers,
        json={"scheduled_time": "09:00:00"},
    )
    delete = client.delete(f"/api/v1/schedules/{schedule['id']}", headers=headers)
    after_delete = client.get("/api/v1/dose-logs", headers=headers)

    assert first.status_code == 200
    assert len(first.json()) == 1
    assert second.json() == first.json()
    assert changed.status_code == 200
    assert delete.status_code == 204
    assert after_delete.json() == first.json()
    assert client.get("/api/v1/schedules", headers=headers).json()[0]["active"] is False


def test_confirm_skip_needs_help_and_dose_authorization(client: TestClient) -> None:
    owner_headers, _, _ = setup_schedule(client, "owner@example.com")
    other_headers, other_medication, _ = setup_schedule(client, "other@example.com")
    owner_dose = client.get("/api/v1/dose-logs/today", headers=owner_headers).json()[0]
    other_dose = client.get("/api/v1/dose-logs/today", headers=other_headers).json()[0]

    confirmed = client.patch(
        f"/api/v1/dose-logs/{owner_dose['id']}/confirm",
        headers=owner_headers,
        json={
            "confirmation_method": "BUTTON",
            "actual_taken_time": owner_dose["scheduled_time"],
            "notes": "User confirmed",
        },
    )
    skipped = client.patch(
        f"/api/v1/dose-logs/{other_dose['id']}/skip",
        headers=other_headers,
        json={"notes": "User chose to skip"},
    )
    unauthorized = client.patch(
        f"/api/v1/dose-logs/{other_dose['id']}/needs-help",
        headers=owner_headers,
        json={},
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "TAKEN_ON_TIME"
    assert skipped.json()["status"] == "SKIPPED"
    assert unauthorized.status_code == 404
    assert other_medication["active"] is True


def test_needs_help_and_resolved_dose_cannot_be_changed(client: TestClient) -> None:
    headers, _, _ = setup_schedule(client)
    dose = client.get("/api/v1/dose-logs/today", headers=headers).json()[0]

    needs_help = client.patch(
        f"/api/v1/dose-logs/{dose['id']}/needs-help",
        headers=headers,
        json={"notes": "User requested assistance"},
    )
    retry = client.patch(
        f"/api/v1/dose-logs/{dose['id']}/skip",
        headers=headers,
        json={},
    )

    assert needs_help.json()["status"] == "NEEDS_HELP"
    assert retry.status_code == 409


def test_confirmation_after_allowed_window_is_taken_late(client: TestClient) -> None:
    headers, _, _ = setup_schedule(client)
    dose = client.get("/api/v1/dose-logs/today", headers=headers).json()[0]
    late_time = datetime.fromisoformat(dose["scheduled_time"]) + timedelta(minutes=31)

    response = client.patch(
        f"/api/v1/dose-logs/{dose['id']}/confirm",
        headers=headers,
        json={"confirmation_method": "VOICE", "actual_taken_time": late_time.isoformat()},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "TAKEN_LATE"


def test_inactive_medication_and_as_needed_do_not_generate(client: TestClient) -> None:
    headers, medication, _ = setup_schedule(client)
    deactivated = client.patch(
        f"/api/v1/medications/{medication['id']}",
        headers=headers,
        json={"active": False},
    )
    as_needed_medication = create_medication(client, headers)
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    as_needed = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "medication_id": as_needed_medication["id"],
            "frequency_type": "AS_NEEDED",
            "start_date": today,
        },
    )
    generated = client.get("/api/v1/dose-logs/today", headers=headers)

    assert deactivated.status_code == 200
    assert as_needed.status_code == 201
    assert generated.json() == []


def test_unauthenticated_schedule_and_dose_access_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/schedules").status_code == 401
    assert client.get("/api/v1/dose-logs").status_code == 401


def test_caregiver_has_no_schedule_bypass_without_link_permission(client: TestClient) -> None:
    tokens = register_user(client, email="caregiver@example.com", role="CAREGIVER")
    headers = bearer(tokens["access_token"])

    schedules = client.get("/api/v1/schedules", headers=headers)
    dose_logs = client.get("/api/v1/dose-logs", headers=headers)

    assert schedules.status_code == 403
    assert dose_logs.status_code == 403
