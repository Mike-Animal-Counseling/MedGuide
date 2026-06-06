from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from app.db.base import Base


class CaregiverPermission(StrEnum):
    VIEW_ONLY = "VIEW_ONLY"
    MANAGE_MEDICATIONS = "MANAGE_MEDICATIONS"
    FULL_ACCESS = "FULL_ACCESS"


class CaregiverLinkStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class CaregiverLink(Base):
    __tablename__ = "caregiver_links"
    __table_args__ = (
        Index("ix_caregiver_links_patient_status", "patient_id", "status"),
        Index("ix_caregiver_links_caregiver_status", "caregiver_id", "status"),
        Index(
            "uq_caregiver_links_unrevoked_email",
            "patient_id",
            "caregiver_email",
            unique=True,
            postgresql_where=text("status != 'REVOKED'"),
            sqlite_where=text("status != 'REVOKED'"),
        ),
        CheckConstraint(
            "status != 'ACTIVE' OR caregiver_id IS NOT NULL",
            name="ck_caregiver_links_active_has_caregiver",
        ),
        CheckConstraint(
            "caregiver_id IS NULL OR caregiver_id != patient_id",
            name="ck_caregiver_links_distinct_users",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    caregiver_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True, default=None
    )
    caregiver_email: Mapped[str] = mapped_column(String(320), index=True)
    relationship: Mapped[str | None] = mapped_column(String(200), default=None)
    permission_level: Mapped[CaregiverPermission] = mapped_column(
        Enum(CaregiverPermission, name="caregiver_permission")
    )
    status: Mapped[CaregiverLinkStatus] = mapped_column(
        Enum(CaregiverLinkStatus, name="caregiver_link_status")
    )
    invite_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invite_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    patient = orm_relationship("User", foreign_keys=[patient_id])
    caregiver = orm_relationship("User", foreign_keys=[caregiver_id])
