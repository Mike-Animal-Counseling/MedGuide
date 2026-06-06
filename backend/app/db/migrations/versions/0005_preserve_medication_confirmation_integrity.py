"""Preserve medication confirmation integrity.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("medications_confirmed_by_fkey", "medications", type_="foreignkey")
    op.create_foreign_key(
        "medications_confirmed_by_fkey",
        "medications",
        "users",
        ["confirmed_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("medications_confirmed_by_fkey", "medications", type_="foreignkey")
    op.create_foreign_key(
        "medications_confirmed_by_fkey",
        "medications",
        "users",
        ["confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )
