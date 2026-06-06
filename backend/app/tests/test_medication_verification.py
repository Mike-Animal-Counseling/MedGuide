import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.ai_verification import AIVerificationEvent, VerificationResult
from app.models.schedule import DoseLog
from app.services.vision import VisionImageRef, VisualFeatures
from app.tests.conftest import register_user
from app.tests.test_label_scan import (
    attach_latest_image,
    readable_image_bytes,
    unreadable_image_bytes,
)
from app.tests.test_schedules import bearer, create_daily_schedule
from app.tests.test_uploads import RecordingStorageProvider, create_image


class MockVisionProvider:
    def __init__(self, features: VisualFeatures) -> None:
        self.features = features
        self.calls = 0

    async def extract_features(self, image_ref: VisionImageRef) -> VisualFeatures:
        self.calls += 1
        assert image_ref.image_bytes
        return self.features


def setup_verification(
    client: TestClient,
    features: VisualFeatures,
    *,
    email: str = "verify-patient@example.com",
) -> tuple[dict[str, str], dict[str, Any], RecordingStorageProvider, MockVisionProvider]:
    app = client.app
    assert isinstance(app, FastAPI)
    storage = RecordingStorageProvider()
    vision = MockVisionProvider(features)
    app.state.storage_provider = storage
    app.state.vision_provider = vision
    app.state.settings.image_quality_min_contrast = 5

    headers = bearer(register_user(client, email=email)["access_token"])
    medication_response = client.post(
        "/api/v1/medications",
        headers=headers,
        json={
            "name": "Current scheduled medication",
            "form": "TABLET",
            "pill_color": "white",
            "pill_shape": "round",
            "imprint": "A1",
            "source": "MANUAL",
            "active": True,
        },
    )
    assert medication_response.status_code == 201
    medication = medication_response.json()
    create_daily_schedule(client, headers, medication["id"])
    dose = client.get("/api/v1/dose-logs/today", headers=headers).json()[0]
    set_dose_due_now(client, dose["id"])
    image = create_image(client, headers, purpose="VERIFICATION_IMAGE")
    attach_latest_image(storage, readable_image_bytes())
    return headers, {"dose": dose, "image": image}, storage, vision


def set_dose_due_now(client: TestClient, dose_log_id: str) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    async def update_time() -> None:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            await session.execute(
                update(DoseLog)
                .where(DoseLog.id == UUID(dose_log_id))
                .values(scheduled_time=datetime.now(UTC))
            )
            await session.commit()

    asyncio.run(update_time())


def verify(client: TestClient, headers: dict[str, str], records: dict[str, Any]) -> Any:
    return client.post(
        "/api/v1/ai/verify-medication",
        headers=headers,
        json={
            "dose_log_id": records["dose"]["id"],
            "image_id": records["image"]["image_id"],
            "verification_type": "PILL_VERIFY",
        },
    )


def verification_event_count(client: TestClient, result: VerificationResult) -> int:
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


def test_high_confidence_match_is_audited_with_safe_language(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(
        client,
        VisualFeatures(colors=("white",), shapes=("round",), visible_imprint="A1"),
    )

    response = verify(client, headers, records)

    assert response.status_code == 200
    assert response.json()["result"] == "MATCH_LIKELY"
    assert response.json()["confidence_score"] == 1
    assert response.json()["requires_confirmation"] is True
    assert "appears" in response.json()["safety_message"].casefold()
    assert verification_event_count(client, VerificationResult.MATCH_LIKELY) == 1


def test_medium_confidence_is_uncertain(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(
        client,
        VisualFeatures(colors=("white",), visible_imprint="A1"),
    )

    response = verify(client, headers, records)

    assert response.status_code == 200
    assert response.json()["result"] == "MATCH_UNCERTAIN"
    assert 0.60 <= response.json()["confidence_score"] < 0.85


def test_low_evidence_requires_caregiver_review(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(client, VisualFeatures())

    response = verify(client, headers, records)

    assert response.status_code == 200
    assert response.json()["result"] == "CAREGIVER_REVIEW_REQUIRED"
    assert "cannot confirm" in response.json()["safety_message"].casefold()


def test_wrong_medication_features_return_no_match(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(
        client,
        VisualFeatures(colors=("blue",), shapes=("capsule",), visible_imprint="ZZ"),
    )

    response = verify(client, headers, records)

    assert response.status_code == 200
    assert response.json()["result"] == "NO_MATCH"
    assert "does not appear" in response.json()["safety_message"].casefold()


def test_unreadable_image_skips_vision_provider(client: TestClient) -> None:
    headers, records, storage, vision = setup_verification(
        client,
        VisualFeatures(colors=("white",), shapes=("round",), visible_imprint="A1"),
    )
    attach_latest_image(storage, unreadable_image_bytes())

    response = verify(client, headers, records)

    assert response.status_code == 200
    assert response.json()["result"] == "UNREADABLE_IMAGE"
    assert vision.calls == 0


def test_unauthorized_user_cannot_verify_another_users_dose(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(client, VisualFeatures())
    other = bearer(register_user(client, email="verify-other@example.com")["access_token"])

    response = verify(client, other, records)

    assert response.status_code == 404
    assert headers != other


def test_full_access_caregiver_can_verify_linked_patients_due_dose(client: TestClient) -> None:
    patient_headers, records, _, _ = setup_verification(
        client,
        VisualFeatures(colors=("white",), shapes=("round",), visible_imprint="A1"),
        email="care-verification-patient@example.com",
    )
    caregiver = register_user(
        client, email="care-verification-caregiver@example.com", role="CAREGIVER"
    )
    caregiver_headers = bearer(caregiver["access_token"])
    invite = client.post(
        "/api/v1/caregivers/invite",
        headers=patient_headers,
        json={
            "caregiver_email": "care-verification-caregiver@example.com",
            "permission_level": "FULL_ACCESS",
        },
    )
    accepted = client.post(
        "/api/v1/caregivers/accept",
        headers=caregiver_headers,
        json={"invite_token": invite.json()["invite_token"]},
    )

    response = verify(client, caregiver_headers, records)

    assert accepted.status_code == 200
    assert response.status_code == 200
    assert response.json()["result"] == "MATCH_LIKELY"


def test_not_currently_due_dose_is_rejected(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(client, VisualFeatures())
    app = client.app
    assert isinstance(app, FastAPI)

    async def move_to_past() -> None:
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            await session.execute(
                update(DoseLog)
                .where(DoseLog.id == UUID(records["dose"]["id"]))
                .values(scheduled_time=datetime(2020, 1, 1, tzinfo=UTC))
            )
            await session.commit()

    asyncio.run(move_to_past())
    response = verify(client, headers, records)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "dose_not_currently_due"


def test_missing_vision_provider_fails_safely(client: TestClient) -> None:
    headers, records, _, _ = setup_verification(client, VisualFeatures())
    from app.services.vision import UnconfiguredVisionProvider

    app = client.app
    assert isinstance(app, FastAPI)
    app.state.vision_provider = UnconfiguredVisionProvider()

    response = verify(client, headers, records)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "vision_provider_not_configured"


def test_all_safety_messages_avoid_certainty_claims(client: TestClient) -> None:
    from app.services.medication_verification import SafetyMessageService

    messages = SafetyMessageService()
    for result in VerificationResult:
        message = messages.build(result, 1)
        assert "definitely" not in message.casefold()
        assert "certainly" not in message.casefold()
        assert "confirmed correct" not in message.casefold()
