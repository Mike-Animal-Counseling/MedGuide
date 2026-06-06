"""Add medication validation constraints.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_medications_name_not_blank",
        "medications",
        "length(trim(name)) > 0",
    )
    op.create_check_constraint(
        "ck_medications_ocr_instructions_require_confirmation",
        "medications",
        "source != 'OCR' OR instructions IS NULL OR confirmed_by IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_medications_ocr_instructions_require_confirmation",
        "medications",
        type_="check",
    )
    op.drop_constraint("ck_medications_name_not_blank", "medications", type_="check")
