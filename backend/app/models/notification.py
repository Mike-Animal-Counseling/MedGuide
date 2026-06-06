from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(StrEnum):
    DOSE_REMINDER = "DOSE_REMINDER"
    SNOOZE_REMINDER = "SNOOZE_REMINDER"
    MISSED_DOSE_ALERT = "MISSED_DOSE_ALERT"
    CAREGIVER_ESCALATION = "CAREGIVER_ESCALATION"
    DAILY_SUMMARY = "DAILY_SUMMARY"


class NotificationChannel(StrEnum):
    PUSH = "PUSH"
    SMS = "SMS"
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class DevicePlatform(StrEnum):
    IOS = "IOS"
    ANDROID = "ANDROID"
    WEB = "WEB"


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        Index("ix_notification_events_user_created", "user_id", "created_at"),
        Index(
            "uq_notification_patient_dose_type_channel",
            "dose_log_id",
            "notification_type",
            "channel",
            unique=True,
            postgresql_where=text("caregiver_id IS NULL AND dose_log_id IS NOT NULL"),
            sqlite_where=text("caregiver_id IS NULL AND dose_log_id IS NOT NULL"),
        ),
        Index(
            "uq_notification_caregiver_dose_type_channel",
            "dose_log_id",
            "caregiver_id",
            "notification_type",
            "channel",
            unique=True,
            postgresql_where=text("caregiver_id IS NOT NULL AND dose_log_id IS NOT NULL"),
            sqlite_where=text("caregiver_id IS NOT NULL AND dose_log_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    caregiver_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), index=True, default=None
    )
    dose_log_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dose_logs.id"), index=True, default=None
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type")
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel")
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
    )
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=None
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class UserDevice(Base):
    __tablename__ = "user_devices"
    __table_args__ = (
        Index("ix_user_devices_user_active", "user_id", "active"),
        Index("uq_user_devices_push_token", "push_token", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[DevicePlatform] = mapped_column(Enum(DevicePlatform, name="device_platform"))
    push_token: Mapped[str] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
