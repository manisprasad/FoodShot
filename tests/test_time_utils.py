from datetime import date, datetime, timedelta

from core import time_utils
from db.models import User
from services.freemium import is_user_premium


def test_get_utc_now():
    now_utc = time_utils.get_utc_now()
    assert isinstance(now_utc, datetime)
    assert now_utc.tzinfo is None


def test_get_local_now():
    local_now = time_utils.get_local_now(offset_hours=3)
    utc_now = time_utils.get_utc_now()
    diff_seconds = (local_now - utc_now).total_seconds()
    # Should be approximately 3 hours (10800 seconds)
    assert 10795 <= diff_seconds <= 10805


def test_to_local_time_and_to_utc_time():
    utc_dt = datetime(2026, 7, 29, 12, 0, 0)
    local_dt = time_utils.to_local_time(utc_dt, offset_hours=3)
    assert local_dt == datetime(2026, 7, 29, 15, 0, 0)

    back_to_utc = time_utils.to_utc_time(local_dt, offset_hours=3)
    assert back_to_utc == utc_dt

    assert time_utils.to_local_time(None) is None


def test_get_local_day_utc_range():
    target = date(2026, 7, 29)
    utc_start, utc_end = time_utils.get_local_day_utc_range(target, offset_hours=3)
    assert utc_start == datetime(2026, 7, 28, 21, 0, 0)
    assert utc_end == datetime(2026, 7, 29, 20, 59, 59, 999999)


def test_get_today_str():
    today_str = time_utils.get_today_str(offset_hours=3)
    expected_str = time_utils.get_local_now(offset_hours=3).strftime("%Y-%m-%d")
    assert today_str == expected_str


def test_is_user_premium_active():
    now = time_utils.get_utc_now()
    active_user = User(
        id=1,
        is_premium=True,
        premium_until=now + timedelta(days=1),
    )
    assert is_user_premium(active_user, now) is True


def test_is_user_premium_expired():
    now = time_utils.get_utc_now()
    expired_user = User(
        id=2,
        is_premium=True,
        premium_until=now - timedelta(seconds=1),
    )
    assert is_user_premium(expired_user, now) is False


def test_is_user_premium_none_until():
    user = User(
        id=3,
        is_premium=True,
        premium_until=None,
    )
    assert is_user_premium(user) is False


def test_is_user_premium_not_flagged():
    now = time_utils.get_utc_now()
    user = User(
        id=4,
        is_premium=False,
        premium_until=now + timedelta(days=1),
    )
    assert is_user_premium(user, now) is False
