"""Add caregiver links.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

caregiver_permission = postgresql.ENUM(
    "VIEW_ONLY",
    "MANAGE_MEDICATIONS",
    "FULL_ACCESS",
    name="caregiver_permission",
    create_type=False,
)
caregiver_link_status = postgresql.ENUM(
    "PENDING",
    "ACTIVE",
    "REVOKED",
    name="caregiver_link_status",
    create_type=False,
)


def upgrade() -> None:
    caregiver_permission.create(op.get_bind(), checkfirst=True)
    caregiver_link_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "caregiver_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("caregiver_id", sa.Uuid(), nullable=True),
        sa.Column("caregiver_email", sa.String(length=320), nullable=False),
        sa.Column("relationship", sa.String(length=200), nullable=True),
        sa.Column("permission_level", caregiver_permission, nullable=False),
        sa.Column("status", caregiver_link_status, nullable=False),
        sa.Column("invite_token_hash", sa.String(length=64), nullable=False),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status != 'ACTIVE' OR caregiver_id IS NOT NULL",
            name="ck_caregiver_links_active_has_caregiver",
        ),
        sa.CheckConstraint(
            "caregiver_id IS NULL OR caregiver_id != patient_id",
            name="ck_caregiver_links_distinct_users",
        ),
        sa.ForeignKeyConstraint(["caregiver_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_token_hash"),
    )
    op.create_index(
        "ix_caregiver_links_caregiver_email",
        "caregiver_links",
        ["caregiver_email"],
        unique=False,
    )
    op.create_index(
        "ix_caregiver_links_caregiver_id",
        "caregiver_links",
        ["caregiver_id"],
        unique=False,
    )
    op.create_index(
        "ix_caregiver_links_caregiver_status",
        "caregiver_links",
        ["caregiver_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_caregiver_links_patient_id",
        "caregiver_links",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_caregiver_links_patient_status",
        "caregiver_links",
        ["patient_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_caregiver_links_unrevoked_email",
        "caregiver_links",
        ["patient_id", "caregiver_email"],
        unique=True,
        postgresql_where=sa.text("status != 'REVOKED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_caregiver_links_unrevoked_email", table_name="caregiver_links")
    op.drop_index("ix_caregiver_links_patient_status", table_name="caregiver_links")
    op.drop_index("ix_caregiver_links_patient_id", table_name="caregiver_links")
    op.drop_index("ix_caregiver_links_caregiver_status", table_name="caregiver_links")
    op.drop_index("ix_caregiver_links_caregiver_id", table_name="caregiver_links")
    op.drop_index("ix_caregiver_links_caregiver_email", table_name="caregiver_links")
    op.drop_table("caregiver_links")
    caregiver_link_status.drop(op.get_bind(), checkfirst=True)
    caregiver_permission.drop(op.get_bind(), checkfirst=True)
