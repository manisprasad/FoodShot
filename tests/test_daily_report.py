from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.i18n import I18n
from services.daily_report import parse_time_string, perform_daily_reports


def test_parse_time_string_valid_formats():
    assert parse_time_string("12:00") == time(12, 0)
    assert parse_time_string("12.30") == time(12, 30)
    assert parse_time_string("12;45") == time(12, 45)
    assert parse_time_string("14/00") == time(14, 0)
    assert parse_time_string(" 12:00 ") == time(12, 0)
    assert parse_time_string("1200") == time(12, 0)
    assert parse_time_string("12") == time(12, 0)
    assert parse_time_string("0") == time(0, 0)
    assert parse_time_string("9:15") == time(9, 15)


def test_parse_time_string_invalid_formats():
    assert parse_time_string("24:00") is None
    assert parse_time_string("12:60") is None
    assert parse_time_string("abc") is None
    assert parse_time_string("") is None
    assert parse_time_string("12345") is None


@pytest.mark.asyncio
async def test_perform_daily_reports_skips_if_not_time():
    bot = AsyncMock()
    # Mock current time at 10:00 AM
    mock_now = datetime.combine(date.today(), time(10, 0))

    user = MagicMock()
    user.id = 111
    user.daily_report_time = time(12, 0)  # Report time is 12:00 (not yet time)

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.SessionLocal") as mock_session_cls,
        patch("services.daily_report.crud") as mock_crud,
    ):
        mock_datetime.now.return_value = mock_now

        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_crud.get_users_for_daily_report = AsyncMock(return_value=[user])

        await perform_daily_reports(bot)

        # get_meal_logs_in_range should NOT be called since user was skipped
        mock_crud.get_meal_logs_in_range.assert_not_called()


@pytest.mark.asyncio
async def test_perform_daily_reports_already_sent():
    bot = AsyncMock()
    # Mock current time at 2:00 PM (14:00)
    mock_now = datetime.combine(date.today(), time(14, 0))
    today_str = date.today().strftime("%Y-%m-%d")

    user = MagicMock()
    user.id = 111
    user.daily_report_time = time(12, 0)  # It is past report time

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.redis_client") as mock_redis,
        patch("services.daily_report.SessionLocal") as mock_session_cls,
        patch("services.daily_report.crud") as mock_crud,
    ):
        mock_datetime.now.return_value = mock_now
        # Redis says report was already sent for today
        lock_key = f"daily_report_sent:{user.id}:{today_str}"
        mock_redis.get.side_effect = lambda k: today_str if k == lock_key else None

        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_crud.get_users_for_daily_report = AsyncMock(return_value=[user])

        await perform_daily_reports(bot)

        # get_meal_logs_in_range should NOT be called since report was already sent
        mock_crud.get_meal_logs_in_range.assert_not_called()


@pytest.mark.asyncio
async def test_perform_daily_reports_deficit_yesterday_mode():
    bot = AsyncMock()
    # Mock current time at 2:00 AM (02:00). Early morning report mode (< 4:00 AM)
    mock_now = datetime.combine(date.today(), time(2, 0))
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    lock_key_date = yesterday_str

    user = MagicMock()
    user.id = 111
    user.language = "en"
    user.daily_calorie_target = 2000
    user.daily_report_time = time(1, 0)  # 1:00 AM report (for yesterday)

    meal = MagicMock()
    meal.kcal = 1200.0  # Deficit

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.redis_client") as mock_redis,
        patch("services.daily_report.SessionLocal") as mock_session_cls,
        patch("services.daily_report.crud") as mock_crud,
    ):
        mock_datetime.now.return_value = mock_now
        mock_redis.get.return_value = None  # Not sent yet

        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_crud.get_users_for_daily_report = AsyncMock(return_value=[user])
        mock_crud.get_meal_logs_in_range = AsyncMock(return_value=[meal])

        await perform_daily_reports(bot)

        # Assert Redis was updated with correct key (yesterday's date)
        expected_lock_key = f"daily_report_sent:{user.id}:{lock_key_date}"
        mock_redis.set.assert_called_once_with(expected_lock_key, "sent", ex=172800)

        # Assert correct message sent
        i18n = I18n("en")
        expected_text = i18n.get("daily-report-header", date=yesterday_str) + i18n.get(
            "daily-report-deficit", target=2000, total=1200, diff=800
        )
        bot.send_message.assert_called_once_with(chat_id=111, text=expected_text)


@pytest.mark.asyncio
async def test_perform_daily_reports_surplus_today_mode():
    bot = AsyncMock()
    # Mock current time at 10:00 PM (22:00)
    mock_now = datetime.combine(date.today(), time(22, 0))
    today_str = date.today().strftime("%Y-%m-%d")

    user = MagicMock()
    user.id = 222
    user.language = "uk"
    user.daily_calorie_target = 1800
    user.daily_report_time = time(21, 0)  # 9:00 PM report (for today)

    meal = MagicMock()
    meal.kcal = 2050.0  # Surplus

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.redis_client") as mock_redis,
        patch("services.daily_report.SessionLocal") as mock_session_cls,
        patch("services.daily_report.crud") as mock_crud,
    ):
        mock_datetime.now.return_value = mock_now
        mock_redis.get.return_value = None

        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_crud.get_users_for_daily_report = AsyncMock(return_value=[user])
        mock_crud.get_meal_logs_in_range = AsyncMock(return_value=[meal])

        await perform_daily_reports(bot)

        # Assert Redis was updated with today's date
        expected_lock_key = f"daily_report_sent:{user.id}:{today_str}"
        mock_redis.set.assert_called_once_with(expected_lock_key, "sent", ex=172800)

        # Assert correct message sent
        i18n = I18n("uk")
        expected_text = i18n.get("daily-report-header", date=today_str) + i18n.get(
            "daily-report-surplus", target=1800, total=2050, diff=250
        )
        bot.send_message.assert_called_once_with(chat_id=222, text=expected_text)
