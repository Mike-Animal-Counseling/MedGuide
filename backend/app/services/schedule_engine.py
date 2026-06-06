from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models.schedule import FrequencyType, MedicationSchedule

DAY_CODES = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def generate_scheduled_times(
    schedule: MedicationSchedule,
    *,
    range_start: date,
    range_end: date,
    timezone: ZoneInfo,
) -> list[datetime]:
    if not schedule.active or schedule.frequency_type is FrequencyType.AS_NEEDED:
        return []
    effective_start = max(range_start, schedule.start_date)
    effective_end = min(range_end, schedule.end_date or range_end)
    if effective_end < effective_start:
        return []
    if schedule.frequency_type is FrequencyType.EVERY_X_HOURS:
        return _generate_interval(schedule, effective_start, effective_end, timezone)
    return _generate_wall_clock(schedule, effective_start, effective_end, timezone)


def local_day_bounds(target_date: date, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(target_date, time.min, timezone).astimezone(UTC)
    end = datetime.combine(target_date + timedelta(days=1), time.min, timezone).astimezone(UTC)
    return start, end


def _generate_wall_clock(
    schedule: MedicationSchedule,
    start_date: date,
    end_date: date,
    timezone: ZoneInfo,
) -> list[datetime]:
    if schedule.scheduled_time is None:
        return []
    scheduled_times: list[datetime] = []
    current = start_date
    while current <= end_date:
        if schedule.frequency_type is FrequencyType.DAILY or _is_scheduled_weekday(
            schedule, current
        ):
            localized = _localize_wall_clock(current, schedule.scheduled_time, timezone)
            if localized is not None:
                scheduled_times.append(localized.astimezone(UTC))
        current += timedelta(days=1)
    return scheduled_times


def _generate_interval(
    schedule: MedicationSchedule,
    start_date: date,
    end_date: date,
    timezone: ZoneInfo,
) -> list[datetime]:
    if schedule.interval_hours is None:
        return []
    anchor_time = schedule.scheduled_time or time.min
    anchor = _localize_wall_clock(schedule.start_date, anchor_time, timezone)
    if anchor is None:
        return []
    range_start_utc, _ = local_day_bounds(start_date, timezone)
    _, range_end_utc = local_day_bounds(end_date, timezone)
    interval = timedelta(hours=schedule.interval_hours)
    current = anchor.astimezone(UTC)
    if current < range_start_utc:
        elapsed = range_start_utc - current
        steps = int(elapsed // interval)
        current += steps * interval
        if current < range_start_utc:
            current += interval
    scheduled_times: list[datetime] = []
    while current < range_end_utc:
        scheduled_times.append(current)
        current += interval
    return scheduled_times


def _is_scheduled_weekday(schedule: MedicationSchedule, target_date: date) -> bool:
    return DAY_CODES[target_date.weekday()] in (schedule.days_of_week or [])


def _localize_wall_clock(
    target_date: date, target_time: time, timezone: ZoneInfo
) -> datetime | None:
    naive = datetime.combine(target_date, target_time)
    localized = naive.replace(tzinfo=timezone, fold=0)
    round_trip = localized.astimezone(UTC).astimezone(timezone).replace(tzinfo=None)
    return localized if round_trip == naive else None
