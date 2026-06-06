"""Add medication schedules and dose logs.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

frequency_type = postgresql.ENUM(
    "DAILY",
    "WEEKLY",
    "EVERY_X_HOURS",
    "AS_NEEDED",
    name="frequency_type",
    create_type=False,
)
dose_status = postgresql.ENUM(
    "PENDING",
    "TAKEN_ON_TIME",
    "TAKEN_LATE",
    "SKIPPED",
    "MISSED",
    "NEEDS_HELP",
    "VERIFICATION_FAILED",
    name="dose_status",
    create_type=False,
)
confirmation_method = postgresql.ENUM(
    "VOICE",
    "BUTTON",
    "CAREGIVER",
    "AUTO_MISSED",
    name="confirmation_method",
    create_type=False,
)


def upgrade() -> None:
    frequency_type.create(op.get_bind(), checkfirst=True)
    dose_status.create(op.get_bind(), checkfirst=True)
    confirmation_method.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "medication_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("frequency_type", frequency_type, nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("days_of_week", postgresql.ARRAY(sa.String(length=3)), nullable=True),
        sa.Column("interval_hours", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("reminder_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_medication_schedules_date_range",
        ),
        sa.CheckConstraint(
            "frequency_type != 'EVERY_X_HOURS' OR interval_hours > 0",
            name="ck_medication_schedules_interval_hours",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_medication_schedules_medication_id",
        "medication_schedules",
        ["medication_id"],
        unique=False,
    )
    op.create_index(
        "ix_medication_schedules_user_active",
        "medication_schedules",
        ["user_id", "active"],
        unique=False,
    )
    op.create_index(
        "ix_medication_schedules_user_id",
        "medication_schedules",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "dose_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_taken_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", dose_status, nullable=False),
        sa.Column("confirmation_method", confirmation_method, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["medication_schedules.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id", "scheduled_time", name="uq_dose_logs_schedule_time"),
    )
    op.create_index("ix_dose_logs_medication_id", "dose_logs", ["medication_id"], unique=False)
    op.create_index("ix_dose_logs_schedule_id", "dose_logs", ["schedule_id"], unique=False)
    op.create_index("ix_dose_logs_user_id", "dose_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_dose_logs_user_scheduled_time",
        "dose_logs",
        ["user_id", "scheduled_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dose_logs_user_scheduled_time", table_name="dose_logs")
    op.drop_index("ix_dose_logs_user_id", table_name="dose_logs")
    op.drop_index("ix_dose_logs_schedule_id", table_name="dose_logs")
    op.drop_index("ix_dose_logs_medication_id", table_name="dose_logs")
    op.drop_table("dose_logs")
    op.drop_index("ix_medication_schedules_user_id", table_name="medication_schedules")
    op.drop_index("ix_medication_schedules_user_active", table_name="medication_schedules")
    op.drop_index("ix_medication_schedules_medication_id", table_name="medication_schedules")
    op.drop_table("medication_schedules")
    confirmation_method.drop(op.get_bind(), checkfirst=True)
    dose_status.drop(op.get_bind(), checkfirst=True)
    frequency_type.drop(op.get_bind(), checkfirst=True)
