from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class PushMessage:
    title: str
    body: str
    data: dict[str, str]


@dataclass(frozen=True)
class ProviderDeliveryResult:
    response: dict[str, Any]
    accepted: bool = True


class NotificationProvider(Protocol):
    async def send_push(
        self, *, push_tokens: list[str], message: PushMessage
    ) -> ProviderDeliveryResult: ...


class SMSNotificationProvider(Protocol):
    async def send_sms(self, *, phone_number: str, message: str) -> ProviderDeliveryResult: ...


class EmailNotificationProvider(Protocol):
    async def send_email(
        self, *, email: str, subject: str, message: str
    ) -> ProviderDeliveryResult: ...


class NotificationProviderNotConfiguredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="notification_provider_not_configured",
            message="Push notification provider is not configured",
            status_code=503,
        )


class ExpoPushNotificationProvider:
    endpoint = "https://exp.host/--/api/v2/push/send"

    def __init__(self, settings: Settings) -> None:
        if settings.expo_push_access_token is None:
            raise NotificationProviderNotConfiguredError()
        self.access_token = settings.expo_push_access_token.get_secret_value()

    async def send_push(
        self, *, push_tokens: list[str], message: PushMessage
    ) -> ProviderDeliveryResult:
        if not push_tokens:
            raise AppError(
                code="notification_recipient_unavailable",
                message="No active push device is registered",
                status_code=409,
            )
        payload = [
            {
                "to": token,
                "title": message.title,
                "body": message.body,
                "data": message.data,
                "sound": "default",
            }
            for token in push_tokens
        ]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(
                code="notification_provider_unavailable",
                message="Push notification provider is temporarily unavailable",
                status_code=503,
            ) from exc
        if not isinstance(result, dict):
            raise AppError(
                code="notification_provider_invalid_response",
                message="Push notification provider returned an invalid response",
                status_code=503,
            )
        tickets = result.get("data")
        accepted = isinstance(tickets, list) and any(
            isinstance(ticket, dict) and ticket.get("status") == "ok" for ticket in tickets
        )
        return ProviderDeliveryResult(response=result, accepted=accepted)


class UnconfiguredNotificationProvider:
    async def send_push(
        self, *, push_tokens: list[str], message: PushMessage
    ) -> ProviderDeliveryResult:
        raise NotificationProviderNotConfiguredError()


def create_notification_provider(settings: Settings) -> NotificationProvider:
    if settings.notification_provider == "expo":
        return ExpoPushNotificationProvider(settings)
    return UnconfiguredNotificationProvider()
