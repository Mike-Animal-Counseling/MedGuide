"""Add notification events and user devices.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

notification_type = postgresql.ENUM(
    "DOSE_REMINDER",
    "SNOOZE_REMINDER",
    "MISSED_DOSE_ALERT",
    "CAREGIVER_ESCALATION",
    "DAILY_SUMMARY",
    name="notification_type",
    create_type=False,
)
notification_channel = postgresql.ENUM(
    "PUSH", "SMS", "EMAIL", "IN_APP", name="notification_channel", create_type=False
)
notification_status = postgresql.ENUM(
    "PENDING", "SENT", "FAILED", "RETRYING", name="notification_status", create_type=False
)
device_platform = postgresql.ENUM(
    "IOS", "ANDROID", "WEB", name="device_platform", create_type=False
)


def upgrade() -> None:
    notification_type.create(op.get_bind(), checkfirst=True)
    notification_channel.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)
    device_platform.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "notification_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("caregiver_id", sa.Uuid(), nullable=True),
        sa.Column("dose_log_id", sa.Uuid(), nullable=True),
        sa.Column("notification_type", notification_type, nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("provider_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["caregiver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["dose_log_id"], ["dose_logs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_events_user_id", "notification_events", ["user_id"])
    op.create_index("ix_notification_events_caregiver_id", "notification_events", ["caregiver_id"])
    op.create_index("ix_notification_events_dose_log_id", "notification_events", ["dose_log_id"])
    op.create_index(
        "ix_notification_events_user_created",
        "notification_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "uq_notification_patient_dose_type_channel",
        "notification_events",
        ["dose_log_id", "notification_type", "channel"],
        unique=True,
        postgresql_where=sa.text("caregiver_id IS NULL AND dose_log_id IS NOT NULL"),
    )
    op.create_index(
        "uq_notification_caregiver_dose_type_channel",
        "notification_events",
        ["dose_log_id", "caregiver_id", "notification_type", "channel"],
        unique=True,
        postgresql_where=sa.text("caregiver_id IS NOT NULL AND dose_log_id IS NOT NULL"),
    )
    op.create_table(
        "user_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform", device_platform, nullable=False),
        sa.Column("push_token", sa.String(length=512), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_devices_user_id", "user_devices", ["user_id"])
    op.create_index("ix_user_devices_user_active", "user_devices", ["user_id", "active"])
    op.create_index("uq_user_devices_push_token", "user_devices", ["push_token"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_user_devices_push_token", table_name="user_devices")
    op.drop_index("ix_user_devices_user_active", table_name="user_devices")
    op.drop_index("ix_user_devices_user_id", table_name="user_devices")
    op.drop_table("user_devices")
    op.drop_index("uq_notification_caregiver_dose_type_channel", table_name="notification_events")
    op.drop_index("uq_notification_patient_dose_type_channel", table_name="notification_events")
    op.drop_index("ix_notification_events_user_created", table_name="notification_events")
    op.drop_index("ix_notification_events_dose_log_id", table_name="notification_events")
    op.drop_index("ix_notification_events_caregiver_id", table_name="notification_events")
    op.drop_index("ix_notification_events_user_id", table_name="notification_events")
    op.drop_table("notification_events")
    device_platform.drop(op.get_bind(), checkfirst=True)
    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_channel.drop(op.get_bind(), checkfirst=True)
    notification_type.drop(op.get_bind(), checkfirst=True)
