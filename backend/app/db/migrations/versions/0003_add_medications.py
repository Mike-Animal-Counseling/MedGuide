"""Add medications.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

medication_form = postgresql.ENUM(
    "TABLET",
    "CAPSULE",
    "LIQUID",
    "INJECTION",
    "OTHER",
    name="medication_form",
    create_type=False,
)
medication_source = postgresql.ENUM(
    "MANUAL",
    "OCR",
    "CAREGIVER",
    name="medication_source",
    create_type=False,
)


def upgrade() -> None:
    medication_form.create(op.get_bind(), checkfirst=True)
    medication_source.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "medications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("generic_name", sa.String(length=300), nullable=True),
        sa.Column("brand_name", sa.String(length=300), nullable=True),
        sa.Column("dosage", sa.String(length=200), nullable=True),
        sa.Column("form", medication_form, nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("with_food", sa.Boolean(), nullable=True),
        sa.Column("pill_color", sa.String(length=100), nullable=True),
        sa.Column("pill_shape", sa.String(length=100), nullable=True),
        sa.Column("imprint", sa.String(length=100), nullable=True),
        sa.Column("label_image_url", sa.Text(), nullable=True),
        sa.Column("pill_image_url", sa.Text(), nullable=True),
        sa.Column("source", medication_source, nullable=False),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source != 'OCR' OR active = false OR confirmed_by IS NOT NULL",
            name="ck_medications_ocr_active_requires_confirmation",
        ),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_medications_user_active",
        "medications",
        ["user_id", "active", "deleted_at"],
        unique=False,
    )
    op.create_index(op.f("ix_medications_user_id"), "medications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_medications_user_id"), table_name="medications")
    op.drop_index("ix_medications_user_active", table_name="medications")
    op.drop_table("medications")
    medication_source.drop(op.get_bind(), checkfirst=True)
    medication_form.drop(op.get_bind(), checkfirst=True)
