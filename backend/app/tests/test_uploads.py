from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.storage import SignedUpload
from app.tests.conftest import register_user
from app.tests.test_caregivers import invite_and_accept


class RecordingStorageProvider:
    name = "test-storage"

    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []
        self.reads: list[str] = []
        self.deletes: list[str] = []
        self.objects: dict[str, bytes] = {}

    async def create_signed_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        max_size_bytes: int,
        exact_size_bytes: int | None,
        expires_in_seconds: int,
        retain_until: datetime | None,
    ) -> SignedUpload:
        self.uploads.append(
            {
                "object_key": object_key,
                "content_type": content_type,
                "max_size_bytes": max_size_bytes,
                "exact_size_bytes": exact_size_bytes,
                "expires_in_seconds": expires_in_seconds,
                "retain_until": retain_until,
            }
        )
        return SignedUpload(
            url="https://signed-upload.example",
            fields={"key": object_key, "Content-Type": content_type},
        )

    async def create_signed_read(self, *, object_key: str, expires_in_seconds: int) -> str:
        self.reads.append(object_key)
        return "https://signed-read.example"

    async def read_object(self, *, object_key: str, max_bytes: int) -> bytes:
        return self.objects[object_key][: max_bytes + 1]

    async def delete_object(self, *, object_key: str) -> None:
        self.deletes.append(object_key)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def storage_for(client: TestClient) -> RecordingStorageProvider:
    app = client.app
    assert isinstance(app, FastAPI)
    storage = RecordingStorageProvider()
    app.state.storage_provider = storage
    return storage


def create_image(
    client: TestClient,
    headers: dict[str, str],
    *,
    purpose: str = "MEDICATION_LABEL",
    patient_id: str | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "purpose": purpose,
        "content_type": "image/jpeg",
        "size_bytes": 1024,
    }
    if patient_id is not None:
        request["patient_id"] = patient_id
    response = client.post("/api/v1/uploads/signed-url", headers=headers, json=request)
    assert response.status_code == 201
    payload: dict[str, Any] = response.json()
    return payload


def test_generate_signed_upload_and_read_urls_with_provider(client: TestClient) -> None:
    storage = storage_for(client)
    tokens = register_user(client)
    headers = bearer(tokens["access_token"])

    created = create_image(client, headers)
    read = client.get(
        f"/api/v1/uploads/{created['image_id']}/signed-read-url",
        headers=headers,
    )

    assert created["upload_url"] == "https://signed-upload.example"
    assert created["expires_in_seconds"] == 300
    assert storage.uploads[0]["content_type"] == "image/jpeg"
    assert storage.uploads[0]["exact_size_bytes"] == 1024
    assert "/images/" in storage.uploads[0]["object_key"]
    assert read.status_code == 200
    assert read.json()["read_url"] == "https://signed-read.example"


def test_reject_invalid_content_type_and_oversized_image(client: TestClient) -> None:
    storage = storage_for(client)
    headers = bearer(register_user(client)["access_token"])

    invalid_type = client.post(
        "/api/v1/uploads/signed-url",
        headers=headers,
        json={"purpose": "PILL_REFERENCE", "content_type": "text/plain"},
    )
    oversized = client.post(
        "/api/v1/uploads/signed-url",
        headers=headers,
        json={
            "purpose": "PILL_REFERENCE",
            "content_type": "image/png",
            "size_bytes": 10_485_761,
        },
    )

    assert invalid_type.status_code == 422
    assert invalid_type.json()["error"]["code"] == "invalid_image_content_type"
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "image_too_large"
    assert storage.uploads == []


def test_unauthorized_user_cannot_read_or_delete_image(client: TestClient) -> None:
    storage_for(client)
    owner = bearer(register_user(client, email="owner@example.com")["access_token"])
    other = bearer(register_user(client, email="other@example.com")["access_token"])
    image = create_image(client, owner)

    read = client.get(
        f"/api/v1/uploads/{image['image_id']}/signed-read-url",
        headers=other,
    )
    delete = client.delete(f"/api/v1/uploads/{image['image_id']}", headers=other)

    assert read.status_code == 404
    assert delete.status_code == 404


def test_delete_calls_provider_and_soft_deletes_record(client: TestClient) -> None:
    storage = storage_for(client)
    headers = bearer(register_user(client)["access_token"])
    image = create_image(client, headers, purpose="PILL_REFERENCE")

    deleted = client.delete(f"/api/v1/uploads/{image['image_id']}", headers=headers)
    read_after_delete = client.get(
        f"/api/v1/uploads/{image['image_id']}/signed-read-url",
        headers=headers,
    )

    assert deleted.status_code == 204
    assert len(storage.deletes) == 1
    assert read_after_delete.status_code == 404


def test_caregiver_image_permissions_are_enforced(client: TestClient) -> None:
    storage_for(client)
    patient_headers, view_headers, _ = invite_and_accept(client)
    patient = client.get("/api/v1/auth/me", headers=patient_headers).json()
    label = create_image(client, patient_headers)
    verification = create_image(client, patient_headers, purpose="VERIFICATION_IMAGE")

    view_label = client.get(
        f"/api/v1/uploads/{label['image_id']}/signed-read-url",
        headers=view_headers,
    )
    view_verification = client.get(
        f"/api/v1/uploads/{verification['image_id']}/signed-read-url",
        headers=view_headers,
    )
    view_upload = client.post(
        "/api/v1/uploads/signed-url",
        headers=view_headers,
        json={
            "purpose": "MEDICATION_LABEL",
            "content_type": "image/jpeg",
            "patient_id": patient["id"],
        },
    )

    assert view_label.status_code == 200
    assert view_verification.status_code == 404
    assert view_upload.status_code == 403


def test_manage_caregiver_can_upload_but_full_access_is_required_for_verification(
    client: TestClient,
) -> None:
    storage_for(client)
    patient_headers, manage_headers, _ = invite_and_accept(
        client,
        patient_email="manage-patient@example.com",
        caregiver_email="manage-caregiver@example.com",
        permission="MANAGE_MEDICATIONS",
    )
    patient = client.get("/api/v1/auth/me", headers=patient_headers).json()

    label = create_image(client, manage_headers, patient_id=patient["id"])
    verification = client.post(
        "/api/v1/uploads/signed-url",
        headers=manage_headers,
        json={
            "purpose": "VERIFICATION_IMAGE",
            "content_type": "image/jpeg",
            "patient_id": patient["id"],
        },
    )

    assert label["image_id"]
    assert verification.status_code == 403


def test_medication_stores_only_owned_private_image_references(client: TestClient) -> None:
    storage_for(client)
    owner_headers = bearer(register_user(client, email="image-owner@example.com")["access_token"])
    other_headers = bearer(register_user(client, email="image-other@example.com")["access_token"])
    label = create_image(client, owner_headers)
    wrong_purpose = create_image(client, owner_headers, purpose="PILL_REFERENCE")
    other_label = create_image(client, other_headers)

    created = client.post(
        "/api/v1/medications",
        headers=owner_headers,
        json={
            "name": "Medication with private image",
            "form": "TABLET",
            "source": "MANUAL",
            "label_image_id": label["image_id"],
        },
    )
    wrong = client.post(
        "/api/v1/medications",
        headers=owner_headers,
        json={
            "name": "Wrong purpose",
            "form": "TABLET",
            "source": "MANUAL",
            "label_image_id": wrong_purpose["image_id"],
        },
    )
    cross_user = client.post(
        "/api/v1/medications",
        headers=owner_headers,
        json={
            "name": "Cross user",
            "form": "TABLET",
            "source": "MANUAL",
            "label_image_id": other_label["image_id"],
        },
    )
    public_url = client.post(
        "/api/v1/medications",
        headers=owner_headers,
        json={
            "name": "Public URL",
            "form": "TABLET",
            "source": "MANUAL",
            "label_image_url": "https://public-bucket.example/image.jpg",
        },
    )

    assert created.status_code == 201
    assert created.json()["label_image_id"] == label["image_id"]
    assert "label_image_url" not in created.json()
    assert wrong.status_code == 404
    assert cross_user.status_code == 404
    assert public_url.status_code == 422
