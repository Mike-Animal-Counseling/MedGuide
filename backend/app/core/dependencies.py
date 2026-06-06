from collections.abc import AsyncIterator
from typing import Annotated, Protocol, cast
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.observability import MetricsService
from app.core.security import (
    Argon2PasswordHasher,
    PasswordHasher,
    TokenManager,
    TokenType,
    authentication_error,
    authorization_error,
)
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.caregiver import CaregiverService
from app.services.device import DeviceService
from app.services.image_quality import PillowImageQualityChecker
from app.services.label_scan import LabelScanService
from app.services.medication import MedicationService
from app.services.medication_verification import MedicationVerificationService
from app.services.notification import NotificationService, UnconfiguredNotificationService
from app.services.ocr import OCRProvider
from app.services.privacy import PrivacyService
from app.services.schedule import DoseLogService, ScheduleService
from app.services.storage import StorageProvider
from app.services.upload import UploadService
from app.services.user import UserService
from app.services.vision import VisionProvider


class HealthChecker(Protocol):
    async def check(self) -> None: ...


bearer_scheme = HTTPBearer(auto_error=False)
password_hasher = Argon2PasswordHasher()
notification_service = UnconfiguredNotificationService()


def get_settings_dependency(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_request_id(request: Request) -> str | None:
    return cast(str | None, getattr(request.state, "request_id", None))


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)
    async with session_factory() as session:
        yield session


def get_database_health_checker(request: Request) -> HealthChecker:
    return cast(HealthChecker, request.app.state.database_health_checker)


def get_redis_health_checker(request: Request) -> HealthChecker:
    return cast(HealthChecker, request.app.state.redis_health_checker)


def get_redis_client(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_storage_provider(request: Request) -> StorageProvider:
    return cast(StorageProvider, request.app.state.storage_provider)


def get_ocr_provider(request: Request) -> OCRProvider:
    return cast(OCRProvider, request.app.state.ocr_provider)


def get_vision_provider(request: Request) -> VisionProvider:
    return cast(VisionProvider, request.app.state.vision_provider)


def get_metrics_service(request: Request) -> MetricsService:
    return cast(MetricsService, request.app.state.metrics)


def get_password_hasher() -> PasswordHasher:
    return password_hasher


def get_token_manager(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> TokenManager:
    return TokenManager(settings)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_manager: Annotated[TokenManager, Depends(get_token_manager)],
    request_id: Annotated[str | None, Depends(get_request_id)],
) -> AuthService:
    return AuthService(session, settings, hasher, token_manager, AuditService(session, request_id))


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    return UserService(session)


def get_device_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeviceService:
    return DeviceService(session)


def get_medication_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request_id: Annotated[str | None, Depends(get_request_id)],
) -> MedicationService:
    return MedicationService(session, AuditService(session, request_id))


def get_notification_service() -> NotificationService:
    return notification_service


def get_caregiver_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    notifications: Annotated[NotificationService, Depends(get_notification_service)],
    request_id: Annotated[str | None, Depends(get_request_id)],
) -> CaregiverService:
    return CaregiverService(session, settings, notifications, AuditService(session, request_id))


def get_schedule_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request_id: Annotated[str | None, Depends(get_request_id)],
) -> ScheduleService:
    return ScheduleService(session, AuditService(session, request_id))


def get_dose_log_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    request_id: Annotated[str | None, Depends(get_request_id)],
    metrics: Annotated[MetricsService, Depends(get_metrics_service)],
) -> DoseLogService:
    return DoseLogService(session, settings, AuditService(session, request_id), metrics)


def get_upload_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    request_id: Annotated[str | None, Depends(get_request_id)],
) -> UploadService:
    return UploadService(session, settings, storage, AuditService(session, request_id))


def get_privacy_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    notifications: Annotated[NotificationService, Depends(get_notification_service)],
    request_id: Annotated[str | None, Depends(get_request_id)],
) -> PrivacyService:
    audit = AuditService(session, request_id)
    return PrivacyService(
        session,
        UploadService(session, settings, storage, audit),
        CaregiverService(session, settings, notifications, audit),
        audit,
    )


def get_label_scan_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    ocr: Annotated[OCRProvider, Depends(get_ocr_provider)],
    request_id: Annotated[str | None, Depends(get_request_id)],
    metrics: Annotated[MetricsService, Depends(get_metrics_service)],
) -> LabelScanService:
    return LabelScanService(
        session,
        settings,
        storage,
        ocr,
        PillowImageQualityChecker(settings),
        AuditService(session, request_id),
        metrics,
    )


def get_medication_verification_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    vision: Annotated[VisionProvider, Depends(get_vision_provider)],
    request_id: Annotated[str | None, Depends(get_request_id)],
    metrics: Annotated[MetricsService, Depends(get_metrics_service)],
) -> MedicationVerificationService:
    return MedicationVerificationService(
        session,
        settings,
        storage,
        vision,
        PillowImageQualityChecker(settings),
        AuditService(session, request_id),
        metrics,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token_manager: Annotated[TokenManager, Depends(get_token_manager)],
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise authentication_error()
    payload = token_manager.decode(credentials.credentials, TokenType.ACCESS)
    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise authentication_error("Invalid token claims") from exc
    user = await UserRepository(session).get_active_by_id(user_id)
    if user is None:
        raise authentication_error("User is unavailable")
    return user


def require_roles(*allowed_roles: UserRole) -> object:
    async def role_dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in allowed_roles:
            raise authorization_error()
        return user

    return role_dependency
