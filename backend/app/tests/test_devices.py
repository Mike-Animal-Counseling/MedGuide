from fastapi.testclient import TestClient

from app.tests.conftest import register_user
from app.tests.test_schedules import bearer


def test_device_registration_update_and_deactivation(client: TestClient) -> None:
    first = bearer(register_user(client, email="device-first@example.com")["access_token"])
    second = bearer(register_user(client, email="device-second@example.com")["access_token"])
    token = "ExpoPushToken[test-device-token]"

    created = client.post(
        "/api/v1/devices",
        headers=first,
        json={"platform": "IOS", "push_token": token},
    )
    transferred = client.post(
        "/api/v1/devices",
        headers=second,
        json={"platform": "ANDROID", "push_token": token},
    )
    old_owner_delete = client.delete(f"/api/v1/devices/{created.json()['id']}", headers=first)
    deleted = client.delete(f"/api/v1/devices/{created.json()['id']}", headers=second)

    assert created.status_code == 201
    assert "push_token" not in created.json()
    assert transferred.status_code == 201
    assert transferred.json()["id"] == created.json()["id"]
    assert transferred.json()["platform"] == "ANDROID"
    assert old_owner_delete.status_code == 404
    assert deleted.status_code == 204


def test_invalid_device_token_and_unauthenticated_registration_fail(client: TestClient) -> None:
    headers = bearer(register_user(client)["access_token"])

    invalid = client.post(
        "/api/v1/devices",
        headers=headers,
        json={"platform": "IOS", "push_token": "not-an-expo-token"},
    )
    unauthorized = client.post(
        "/api/v1/devices",
        json={"platform": "IOS", "push_token": "ExpoPushToken[valid-token]"},
    )

    assert invalid.status_code == 422
    assert unauthorized.status_code == 401
