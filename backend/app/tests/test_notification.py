import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.services.notification import UnconfiguredNotificationService
from app.services.push_notification import (
    ExpoPushNotificationProvider,
    NotificationProviderNotConfiguredError,
    PushMessage,
    create_notification_provider,
)
from app.tests.test_storage import configured_ocr, configured_storage, production_settings


async def test_unconfigured_notification_service_fails_safely() -> None:
    with pytest.raises(AppError, match="not configured") as exc_info:
        await UnconfiguredNotificationService().send_caregiver_invite(
            caregiver_email="caregiver@example.com",
            patient_name="Patient",
            invite_token="secret-token",
        )

    assert exc_info.value.status_code == 503


async def test_unconfigured_push_provider_fails_safely() -> None:
    provider = create_notification_provider(Settings())

    with pytest.raises(NotificationProviderNotConfiguredError):
        await provider.send_push(
            push_tokens=["ExpoPushToken[test]"],
            message=PushMessage(title="Reminder", body="Body", data={}),
        )


def test_production_requires_expo_push_configuration() -> None:
    configured_vision = {
        "vision_provider": "aws_rekognition",
        "aws_rekognition_region": "us-east-1",
        "aws_rekognition_access_key_id": "test-access",
        "aws_rekognition_secret_access_key": "test-secret",
    }
    with pytest.raises(ValidationError, match="notification provider"):
        Settings(
            **production_settings(
                **configured_storage(),
                **configured_ocr(),
                **configured_vision,
            )
        )
    with pytest.raises(ValidationError, match="Expo push access token"):
        Settings(
            **production_settings(
                **configured_storage(),
                **configured_ocr(),
                **configured_vision,
                notification_provider="expo",
            )
        )


def test_expo_provider_sends_real_adapter_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"data": [{"status": "ok"}]}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client"] = kwargs

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> FakeResponse:
            captured["url"] = url
            captured["request"] = kwargs
            return FakeResponse()

    monkeypatch.setattr("app.services.push_notification.httpx.AsyncClient", FakeClient)
    provider = ExpoPushNotificationProvider(
        Settings(
            notification_provider="expo",
            expo_push_access_token="test-expo-access-token",
        )
    )

    async def send() -> None:
        result = await provider.send_push(
            push_tokens=["ExpoPushToken[test]"],
            message=PushMessage(title="Reminder", body="Safe body", data={"id": "1"}),
        )
        assert result.response["data"]

    import asyncio

    asyncio.run(send())
    assert captured["url"] == ExpoPushNotificationProvider.endpoint
