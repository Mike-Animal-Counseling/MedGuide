"""Add AI verification events.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

verification_type = postgresql.ENUM(
    "LABEL_OCR",
    "PILL_VERIFY",
    "BOTTLE_VERIFY",
    name="verification_type",
    create_type=False,
)
verification_result = postgresql.ENUM(
    "MATCH_LIKELY",
    "MATCH_UNCERTAIN",
    "NO_MATCH",
    "UNREADABLE_IMAGE",
    "CAREGIVER_REVIEW_REQUIRED",
    name="verification_result",
    create_type=False,
)


def upgrade() -> None:
    verification_type.create(op.get_bind(), checkfirst=True)
    verification_result.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "ai_verification_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=True),
        sa.Column("dose_log_id", sa.Uuid(), nullable=True),
        sa.Column("image_id", sa.Uuid(), nullable=True),
        sa.Column("verification_type", verification_type, nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("extracted_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("visual_features", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("result", verification_result, nullable=False),
        sa.Column("safety_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dose_log_id"], ["dose_logs.id"]),
        sa.ForeignKeyConstraint(["image_id"], ["uploaded_images.id"]),
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_verification_events_dose_log_id",
        "ai_verification_events",
        ["dose_log_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_verification_events_image_id",
        "ai_verification_events",
        ["image_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_verification_events_medication_id",
        "ai_verification_events",
        ["medication_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_verification_events_user_id",
        "ai_verification_events",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_verification_events_user_id", table_name="ai_verification_events")
    op.drop_index("ix_ai_verification_events_medication_id", table_name="ai_verification_events")
    op.drop_index("ix_ai_verification_events_image_id", table_name="ai_verification_events")
    op.drop_index("ix_ai_verification_events_dose_log_id", table_name="ai_verification_events")
    op.drop_table("ai_verification_events")
    verification_result.drop(op.get_bind(), checkfirst=True)
    verification_type.drop(op.get_bind(), checkfirst=True)
