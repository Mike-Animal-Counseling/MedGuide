import asyncio
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User, UserRole
from app.tests.conftest import register_user


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def medication_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "User confirmed medication",
        "generic_name": "Confirmed generic name",
        "dosage": "User-entered label text",
        "form": "TABLET",
        "instructions": "User-confirmed instructions from the medication label",
        "with_food": None,
        "source": "MANUAL",
        "active": True,
    }
    payload.update(overrides)
    return payload


def test_create_medication(client: TestClient) -> None:
    tokens = register_user(client)

    response = client.post(
        "/api/v1/medications",
        headers=bearer(tokens["access_token"]),
        json=medication_payload(),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "User confirmed medication"
    assert response.json()["instructions"] == (
        "User-confirmed instructions from the medication label"
    )
    assert response.json()["source"] == "MANUAL"


def test_list_only_own_medications_and_cannot_access_another_users_record(
    client: TestClient,
) -> None:
    first_tokens = register_user(client, email="first@example.com")
    second_tokens = register_user(client, email="second@example.com")
    created = client.post(
        "/api/v1/medications",
        headers=bearer(first_tokens["access_token"]),
        json=medication_payload(),
    ).json()

    second_list = client.get("/api/v1/medications", headers=bearer(second_tokens["access_token"]))
    second_get = client.get(
        f"/api/v1/medications/{created['id']}",
        headers=bearer(second_tokens["access_token"]),
    )
    second_patch = client.patch(
        f"/api/v1/medications/{created['id']}",
        headers=bearer(second_tokens["access_token"]),
        json={"name": "Unauthorized change"},
    )
    second_delete = client.delete(
        f"/api/v1/medications/{created['id']}",
        headers=bearer(second_tokens["access_token"]),
    )

    assert second_list.status_code == 200
    assert second_list.json() == []
    assert second_get.status_code == 404
    assert second_get.json()["error"]["code"] == "medication_not_found"
    assert second_patch.status_code == 404
    assert second_delete.status_code == 404


def test_soft_delete_hides_medication(client: TestClient) -> None:
    tokens = register_user(client)
    headers = bearer(tokens["access_token"])
    created = client.post("/api/v1/medications", headers=headers, json=medication_payload()).json()

    delete_response = client.delete(f"/api/v1/medications/{created['id']}", headers=headers)
    list_response = client.get("/api/v1/medications", headers=headers)
    get_response = client.get(f"/api/v1/medications/{created['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert list_response.json() == []
    assert get_response.status_code == 404


def test_invalid_payload_fails_without_echoing_input(client: TestClient) -> None:
    tokens = register_user(client)

    response = client.post(
        "/api/v1/medications",
        headers=bearer(tokens["access_token"]),
        json=medication_payload(name="   ", form="UNKNOWN"),
    )

    assert response.status_code == 422
    assert "UNKNOWN" not in response.text


def test_ocr_medication_requires_owner_confirmation_before_active(client: TestClient) -> None:
    tokens = register_user(client)
    headers = bearer(tokens["access_token"])

    create_response = client.post(
        "/api/v1/medications",
        headers=headers,
        json=medication_payload(source="OCR", active=True, instructions=None),
    )
    medication = create_response.json()
    me = client.get("/api/v1/auth/me", headers=headers).json()
    confirm_response = client.patch(
        f"/api/v1/medications/{medication['id']}",
        headers=headers,
        json={"confirmed_by": me["id"], "active": True},
    )

    assert create_response.status_code == 201
    assert medication["active"] is False
    assert medication["confirmed_by"] is None
    assert confirm_response.status_code == 200
    assert confirm_response.json()["active"] is True
    assert confirm_response.json()["confirmed_by"] == me["id"]


def test_unconfirmed_ocr_instructions_are_rejected(client: TestClient) -> None:
    tokens = register_user(client)

    response = client.post(
        "/api/v1/medications",
        headers=bearer(tokens["access_token"]),
        json=medication_payload(source="OCR", instructions="Unconfirmed OCR output"),
    )

    assert response.status_code == 422
    assert "Unconfirmed OCR output" not in response.text


def test_unconfirmed_ocr_instructions_cannot_be_added_by_update(client: TestClient) -> None:
    tokens = register_user(client)
    headers = bearer(tokens["access_token"])
    medication = client.post(
        "/api/v1/medications",
        headers=headers,
        json=medication_payload(source="OCR", instructions=None),
    ).json()

    response = client.patch(
        f"/api/v1/medications/{medication['id']}",
        headers=headers,
        json={"instructions": "Unconfirmed OCR output"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "medication_confirmation_required"


def test_other_user_cannot_confirm_ocr_medication(client: TestClient) -> None:
    owner_tokens = register_user(client, email="owner@example.com")
    other_tokens = register_user(client, email="other@example.com")
    owner_headers = bearer(owner_tokens["access_token"])
    other_user = client.get("/api/v1/auth/me", headers=bearer(other_tokens["access_token"])).json()
    medication = client.post(
        "/api/v1/medications",
        headers=owner_headers,
        json=medication_payload(source="OCR", instructions=None),
    ).json()

    response = client.patch(
        f"/api/v1/medications/{medication['id']}",
        headers=owner_headers,
        json={"confirmed_by": other_user["id"], "active": True},
    )

    assert response.status_code == 403


def test_caregiver_has_no_medication_bypass_without_link_permission(client: TestClient) -> None:
    tokens = register_user(client, email="caregiver@example.com", role="CAREGIVER")

    response = client.get("/api/v1/medications", headers=bearer(tokens["access_token"]))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_caregiver_source_requires_future_link_permission(client: TestClient) -> None:
    tokens = register_user(client)

    response = client.post(
        "/api/v1/medications",
        headers=bearer(tokens["access_token"]),
        json=medication_payload(source="CAREGIVER"),
    )

    assert response.status_code == 403


def test_admin_has_no_default_medication_bypass(client: TestClient) -> None:
    tokens = register_user(client, email="future-admin@example.com")
    app = client.app
    assert isinstance(app, FastAPI)

    async def promote_to_admin() -> None:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            await session.execute(
                update(User)
                .where(User.email == "future-admin@example.com")
                .values(role=UserRole.ADMIN)
            )
            await session.commit()

    asyncio.run(promote_to_admin())
    response = client.get("/api/v1/medications", headers=bearer(tokens["access_token"]))

    assert response.status_code == 403


def test_medication_update_does_not_allow_source_change(client: TestClient) -> None:
    tokens = register_user(client)
    headers = bearer(tokens["access_token"])
    created = client.post("/api/v1/medications", headers=headers, json=medication_payload()).json()

    response = client.patch(
        f"/api/v1/medications/{created['id']}",
        headers=headers,
        json={"source": "OCR"},
    )

    assert response.status_code == 422
