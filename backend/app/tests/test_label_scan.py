import asyncio
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.ai_verification import AIVerificationEvent, VerificationResult
from app.services.ocr import OCRResult
from app.tests.conftest import register_user
from app.tests.test_caregivers import invite_and_accept
from app.tests.test_uploads import RecordingStorageProvider, bearer, create_image


class MockOCRProvider:
    def __init__(self, result: OCRResult) -> None:
        self.result = result
        self.calls = 0

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        self.calls += 1
        return self.result


def readable_image_bytes() -> bytes:
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    for position in range(0, 800, 20):
        draw.rectangle((position, 0, position + 10, 600), fill="black")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def unreadable_image_bytes() -> bytes:
    image = Image.new("RGB", (200, 100), "white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def configure_pipeline(
    client: TestClient, ocr_result: OCRResult
) -> tuple[RecordingStorageProvider, MockOCRProvider]:
    app = client.app
    assert isinstance(app, FastAPI)
    storage = RecordingStorageProvider()
    ocr = MockOCRProvider(ocr_result)
    app.state.storage_provider = storage
    app.state.ocr_provider = ocr
    app.state.settings.image_quality_min_contrast = 5
    return storage, ocr


def attach_latest_image(storage: RecordingStorageProvider, image_bytes: bytes) -> None:
    object_key = str(storage.uploads[-1]["object_key"])
    storage.objects[object_key] = image_bytes


def event_count(client: TestClient, result: VerificationResult) -> int:
    app = client.app
    assert isinstance(app, FastAPI)

    async def count() -> int:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            value = await session.scalar(
                select(func.count(AIVerificationEvent.id)).where(
                    AIVerificationEvent.result == result
                )
            )
            return int(value or 0)

    return asyncio.run(count())


def test_ocr_success_logs_event_and_requires_confirmation(client: TestClient) -> None:
    storage, ocr = configure_pipeline(
        client,
        OCRResult(
            text="ExampleMed\n10 mg tablet\nTake one tablet daily",
            confidence=0.91,
        ),
    )
    headers = bearer(register_user(client)["access_token"])
    image = create_image(client, headers)
    attach_latest_image(storage, readable_image_bytes())

    response = client.post(
        "/api/v1/ai/scan-label",
        headers=headers,
        json={"image_id": image["image_id"]},
    )
    medications = client.get("/api/v1/medications", headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] == "LABEL_READ"
    assert response.json()["extracted_fields"]["medication_name"] == "ExampleMed"
    assert response.json()["extracted_fields"]["dosage"] == "10 mg tablet"
    assert response.json()["extracted_fields"]["instructions"] == "Take one tablet daily"
    assert response.json()["requires_confirmation"] is True
    assert "confirm" in response.json()["safety_message"].casefold()
    assert medications.json() == []
    assert ocr.calls == 1
    assert event_count(client, VerificationResult.CAREGIVER_REVIEW_REQUIRED) == 1


def test_unreadable_image_does_not_call_ocr_and_logs_event(client: TestClient) -> None:
    storage, ocr = configure_pipeline(
        client,
        OCRResult(text="must not be used", confidence=1),
    )
    headers = bearer(register_user(client)["access_token"])
    image = create_image(client, headers)
    attach_latest_image(storage, unreadable_image_bytes())

    response = client.post(
        "/api/v1/ai/scan-label",
        headers=headers,
        json={"image_id": image["image_id"]},
    )

    assert response.status_code == 200
    assert response.json()["result"] == "UNREADABLE_IMAGE"
    assert response.json()["ocr_text"] is None
    assert response.json()["requires_confirmation"] is True
    assert ocr.calls == 0
    assert event_count(client, VerificationResult.UNREADABLE_IMAGE) == 1


def test_unauthorized_image_access_is_denied(client: TestClient) -> None:
    storage, _ = configure_pipeline(client, OCRResult(text="ExampleMed", confidence=0.8))
    owner = bearer(register_user(client, email="scan-owner@example.com")["access_token"])
    other = bearer(register_user(client, email="scan-other@example.com")["access_token"])
    image = create_image(client, owner)
    attach_latest_image(storage, readable_image_bytes())

    response = client.post(
        "/api/v1/ai/scan-label",
        headers=other,
        json={"image_id": image["image_id"]},
    )

    assert response.status_code == 404


def test_only_full_access_caregiver_can_scan_label(client: TestClient) -> None:
    storage, _ = configure_pipeline(client, OCRResult(text="ExampleMed", confidence=0.8))
    patient_headers, view_headers, _ = invite_and_accept(client)
    image = create_image(client, patient_headers)
    attach_latest_image(storage, readable_image_bytes())
    denied = client.post(
        "/api/v1/ai/scan-label",
        headers=view_headers,
        json={"image_id": image["image_id"]},
    )

    assert denied.status_code == 404


def test_full_access_caregiver_can_scan_label(client: TestClient) -> None:
    storage, _ = configure_pipeline(client, OCRResult(text="ExampleMed", confidence=0.8))
    patient_headers, caregiver_headers, _ = invite_and_accept(
        client,
        patient_email="full-patient@example.com",
        caregiver_email="full-caregiver@example.com",
        permission="FULL_ACCESS",
    )
    image = create_image(client, patient_headers)
    attach_latest_image(storage, readable_image_bytes())

    response = client.post(
        "/api/v1/ai/scan-label",
        headers=caregiver_headers,
        json={"image_id": image["image_id"]},
    )

    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True


def test_missing_ocr_provider_returns_safe_error(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    storage = RecordingStorageProvider()
    app.state.storage_provider = storage
    headers = bearer(register_user(client)["access_token"])
    image = create_image(client, headers)
    attach_latest_image(storage, readable_image_bytes())

    response = client.post(
        "/api/v1/ai/scan-label",
        headers=headers,
        json={"image_id": image["image_id"]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ocr_provider_not_configured"
