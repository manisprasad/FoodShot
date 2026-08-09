from datetime import UTC, date, datetime, time, timedelta

from core.config import config


def get_utc_now() -> datetime:
    """Return current naive UTC datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


def get_local_offset(offset_hours: float | None = None) -> float:
    """Return offset hours, defaulting to config.TIMEZONE_OFFSET_HOURS."""
    return config.TIMEZONE_OFFSET_HOURS if offset_hours is None else float(offset_hours)


def get_local_now(offset_hours: float | None = None) -> datetime:
    """Return current local naive datetime for a given timezone offset."""
    offset = get_local_offset(offset_hours)
    return get_utc_now() + timedelta(hours=offset)


def to_local_time(
    dt: datetime | None, offset_hours: float | None = None
) -> datetime | None:
    """Convert naive UTC datetime to local naive datetime."""
    if dt is None:
        return None
    offset = get_local_offset(offset_hours)
    return dt + timedelta(hours=offset)


def to_utc_time(dt: datetime, offset_hours: float | None = None) -> datetime:
    """Convert local naive datetime to naive UTC datetime."""
    offset = get_local_offset(offset_hours)
    return dt - timedelta(hours=offset)


def get_today_str(offset_hours: float | None = None) -> str:
    """Return today's date string (YYYY-MM-DD) in local time."""
    return get_local_now(offset_hours).strftime("%Y-%m-%d")


def get_local_day_utc_range(
    target_date: date | None = None, offset_hours: float | None = None
) -> tuple[datetime, datetime]:
    """Calculate exact UTC start and end bounds for a given local date.

    Example: for offset +3 and target_date 2026-07-29,
    local day is [2026-07-29 00:00:00, 2026-07-29 23:59:59.999999],
    which corresponds to UTC [2026-07-28 21:00:00, 2026-07-29 20:59:59.999999].
    """
    offset = get_local_offset(offset_hours)
    if target_date is None:
        target_date = get_local_now(offset_hours).date()

    local_start = datetime.combine(target_date, time.min)
    local_end = datetime.combine(target_date, time.max)

    utc_start = local_start - timedelta(hours=offset)
    utc_end = local_end - timedelta(hours=offset)
    return utc_start, utc_end
