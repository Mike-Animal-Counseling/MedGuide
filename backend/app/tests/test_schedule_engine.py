from datetime import UTC, date, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.models.schedule import FrequencyType, MedicationSchedule
from app.services.schedule_engine import generate_scheduled_times, local_day_bounds


def schedule(**overrides: object) -> MedicationSchedule:
    values: dict[str, object] = {
        "id": uuid4(),
        "medication_id": uuid4(),
        "user_id": uuid4(),
        "frequency_type": FrequencyType.DAILY,
        "scheduled_time": time(8, 30),
        "days_of_week": None,
        "interval_hours": None,
        "start_date": date(2026, 6, 1),
        "end_date": None,
        "reminder_offset_minutes": 0,
        "active": True,
        "created_by": uuid4(),
    }
    values.update(overrides)
    return MedicationSchedule(**values)


def test_daily_schedule_generation_is_timezone_aware() -> None:
    generated = generate_scheduled_times(
        schedule(),
        range_start=date(2026, 6, 1),
        range_end=date(2026, 6, 2),
        timezone=ZoneInfo("America/Chicago"),
    )

    assert generated == [
        datetime(2026, 6, 1, 13, 30, tzinfo=UTC),
        datetime(2026, 6, 2, 13, 30, tzinfo=UTC),
    ]


def test_weekly_schedule_generation_uses_selected_days() -> None:
    generated = generate_scheduled_times(
        schedule(frequency_type=FrequencyType.WEEKLY, days_of_week=["MON", "WED"]),
        range_start=date(2026, 6, 1),
        range_end=date(2026, 6, 7),
        timezone=ZoneInfo("UTC"),
    )

    assert generated == [
        datetime(2026, 6, 1, 8, 30, tzinfo=UTC),
        datetime(2026, 6, 3, 8, 30, tzinfo=UTC),
    ]


def test_every_x_hours_uses_elapsed_time_from_local_anchor() -> None:
    generated = generate_scheduled_times(
        schedule(
            frequency_type=FrequencyType.EVERY_X_HOURS,
            scheduled_time=time(6),
            interval_hours=8,
        ),
        range_start=date(2026, 6, 2),
        range_end=date(2026, 6, 2),
        timezone=ZoneInfo("America/Chicago"),
    )

    assert generated == [
        datetime(2026, 6, 2, 11, tzinfo=UTC),
        datetime(2026, 6, 2, 19, tzinfo=UTC),
        datetime(2026, 6, 3, 3, tzinfo=UTC),
    ]


def test_generation_respects_bounds_inactive_and_as_needed() -> None:
    bounded = generate_scheduled_times(
        schedule(start_date=date(2026, 6, 2), end_date=date(2026, 6, 2)),
        range_start=date(2026, 6, 1),
        range_end=date(2026, 6, 3),
        timezone=ZoneInfo("UTC"),
    )
    inactive = generate_scheduled_times(
        schedule(active=False),
        range_start=date(2026, 6, 1),
        range_end=date(2026, 6, 1),
        timezone=ZoneInfo("UTC"),
    )
    as_needed = generate_scheduled_times(
        schedule(frequency_type=FrequencyType.AS_NEEDED, scheduled_time=None),
        range_start=date(2026, 6, 1),
        range_end=date(2026, 6, 1),
        timezone=ZoneInfo("UTC"),
    )

    assert bounded == [datetime(2026, 6, 2, 8, 30, tzinfo=UTC)]
    assert inactive == []
    assert as_needed == []


def test_nonexistent_dst_wall_clock_is_not_invented() -> None:
    generated = generate_scheduled_times(
        schedule(start_date=date(2026, 3, 8), scheduled_time=time(2, 30)),
        range_start=date(2026, 3, 8),
        range_end=date(2026, 3, 8),
        timezone=ZoneInfo("America/Chicago"),
    )

    assert generated == []


def test_local_day_bounds_follow_dst_day_length() -> None:
    start, end = local_day_bounds(date(2026, 3, 8), ZoneInfo("America/Chicago"))

    assert (end - start).total_seconds() == 23 * 60 * 60
