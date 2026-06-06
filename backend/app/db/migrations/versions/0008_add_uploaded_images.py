"""Add uploaded images.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

image_purpose = postgresql.ENUM(
    "MEDICATION_LABEL",
    "PILL_REFERENCE",
    "VERIFICATION_IMAGE",
    name="image_purpose",
    create_type=False,
)


def upgrade() -> None:
    image_purpose.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "uploaded_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("purpose", image_purpose, nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        "ix_uploaded_images_user_active",
        "uploaded_images",
        ["user_id", "deleted_at"],
        unique=False,
    )
    op.create_index("ix_uploaded_images_user_id", "uploaded_images", ["user_id"], unique=False)
    op.add_column("medications", sa.Column("label_image_id", sa.Uuid(), nullable=True))
    op.add_column("medications", sa.Column("pill_image_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_medications_label_image_id_uploaded_images",
        "medications",
        "uploaded_images",
        ["label_image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_medications_pill_image_id_uploaded_images",
        "medications",
        "uploaded_images",
        ["pill_image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_medications_label_image_id",
        "medications",
        ["label_image_id"],
        unique=False,
    )
    op.create_index("ix_medications_pill_image_id", "medications", ["pill_image_id"], unique=False)
    legacy_reference_count = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM medications "
                "WHERE label_image_url IS NOT NULL OR pill_image_url IS NOT NULL"
            )
        )
        .scalar_one()
    )
    if legacy_reference_count:
        raise RuntimeError(
            "Legacy medication image URLs must be migrated to private uploaded_images records "
            "before applying revision 0008"
        )
    op.drop_column("medications", "label_image_url")
    op.drop_column("medications", "pill_image_url")


def downgrade() -> None:
    op.add_column("medications", sa.Column("pill_image_url", sa.Text(), nullable=True))
    op.add_column("medications", sa.Column("label_image_url", sa.Text(), nullable=True))
    op.drop_index("ix_medications_pill_image_id", table_name="medications")
    op.drop_index("ix_medications_label_image_id", table_name="medications")
    op.drop_constraint(
        "fk_medications_pill_image_id_uploaded_images", "medications", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_medications_label_image_id_uploaded_images", "medications", type_="foreignkey"
    )
    op.drop_column("medications", "pill_image_id")
    op.drop_column("medications", "label_image_id")
    op.drop_index("ix_uploaded_images_user_id", table_name="uploaded_images")
    op.drop_index("ix_uploaded_images_user_active", table_name="uploaded_images")
    op.drop_table("uploaded_images")
    image_purpose.drop(op.get_bind(), checkfirst=True)
