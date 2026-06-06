from typing import Protocol

from app.core.errors import AppError


class NotificationService(Protocol):
    async def send_caregiver_invite(
        self,
        *,
        caregiver_email: str,
        patient_name: str,
        invite_token: str,
    ) -> None: ...


class UnconfiguredNotificationService:
    async def send_caregiver_invite(
        self,
        *,
        caregiver_email: str,
        patient_name: str,
        invite_token: str,
    ) -> None:
        raise AppError(
            code="notification_provider_unconfigured",
            message="Caregiver invite delivery is not configured",
            status_code=503,
        )
