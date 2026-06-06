from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImagePurpose(StrEnum):
    MEDICATION_LABEL = "MEDICATION_LABEL"
    PILL_REFERENCE = "PILL_REFERENCE"
    VERIFICATION_IMAGE = "VERIFICATION_IMAGE"


class UploadedImage(Base):
    __tablename__ = "uploaded_images"
    __table_args__ = (Index("ix_uploaded_images_user_active", "user_id", "deleted_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    provider: Mapped[str] = mapped_column(String(50))
    purpose: Mapped[ImagePurpose] = mapped_column(Enum(ImagePurpose, name="image_purpose"))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
