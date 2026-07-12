from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.i18n import I18n
from services.daily_report import REDIS_REPORT_LOCK_KEY, perform_daily_reports


@pytest.mark.asyncio
async def test_perform_daily_reports_before_1_am():
    bot = AsyncMock()
    # Mock time at 12:30 AM
    mock_now = datetime.combine(date.today(), datetime.min.time()) + timedelta(
        minutes=30
    )

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.redis_client") as mock_redis,
    ):
        mock_datetime.now.return_value = mock_now

        await perform_daily_reports(bot)

        mock_redis.get.assert_not_called()


@pytest.mark.asyncio
async def test_perform_daily_reports_already_run():
    bot = AsyncMock()
    # Mock time at 2:00 AM
    mock_now = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=2)
    today_str = date.today().strftime("%Y-%m-%d")

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.redis_client") as mock_redis,
    ):
        mock_datetime.now.return_value = mock_now
        mock_redis.get.return_value = today_str

        await perform_daily_reports(bot)

        mock_redis.get.assert_called_once_with(REDIS_REPORT_LOCK_KEY)
        # Should not call database SessionLocal
        with patch("services.daily_report.SessionLocal") as mock_session_local:
            await perform_daily_reports(bot)
            mock_session_local.assert_not_called()


@pytest.mark.asyncio
async def test_perform_daily_reports_deficit():
    bot = AsyncMock()
    # Mock time at 2:00 AM
    mock_now = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=2)
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = date.today().strftime("%Y-%m-%d")

    user = MagicMock()
    user.id = 111
    user.language = "en"
    user.daily_calorie_target = 2000

    meal = MagicMock()
    meal.kcal = 1200.0  # Deficit (1200 < 2000 - 100)

    with (
        patch("services.daily_report.datetime") as mock_datetime,
        patch("services.daily_report.redis_client") as mock_redis,
        patch("services.daily_report.SessionLocal") as mock_session_cls,
        patch("services.daily_report.crud") as mock_crud,
    ):
        mock_datetime.now.return_value = mock_now
        mock_redis.get.return_value = None  # Not run yet today

        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        mock_crud.get_users_for_daily_report = AsyncMock(return_value=[user])
        mock_crud.get_meal_logs_in_range = AsyncMock(return_value=[meal])

        await perform_daily_reports(bot)

        # Assert Redis was updated
        mock_redis.set.assert_called_once_with(REDIS_REPORT_LOCK_KEY, today_str)

        # Assert correct message sent
        i18n = I18n("en")
        expected_text = i18n.get("daily-report-header", date=yesterday_str) + i18n.get(
            "daily-report-deficit", target=2000, total=1200, diff=800
        )
        bot.send_message.assert_called_once_with(chat_id=111, text=expected_text)


@pytest.mark.asyncio
async def test_perform_daily_reports_surplus():
    bot = AsyncMock()
    mock_now = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=2)
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    user = MagicMock()
    user.id = 222
    user.language = "uk"
    user.daily_calorie_target = 1800

    meal1 = MagicMock()
    meal1.kcal = 1100.0
    meal2 = MagicMock()
    meal2.kcal = 950.0  # Total 2050. Surplus (2050 > 1800 + 100)

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
        mock_crud.get_meal_logs_in_range = AsyncMock(return_value=[meal1, meal2])

        await perform_daily_reports(bot)

        # Assert correct message sent in Ukrainian
        i18n = I18n("uk")
        expected_text = i18n.get("daily-report-header", date=yesterday_str) + i18n.get(
            "daily-report-surplus", target=1800, total=2050, diff=250
        )
        bot.send_message.assert_called_once_with(chat_id=222, text=expected_text)


@pytest.mark.asyncio
async def test_perform_daily_reports_norm():
    bot = AsyncMock()
    mock_now = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=2)
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    user = MagicMock()
    user.id = 333
    user.language = "en"
    user.daily_calorie_target = 2000

    meal1 = MagicMock()
    meal1.kcal = 1950.0  # Total 1950. Norm (within 100 buffer: 1900 to 2100)

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
        mock_crud.get_meal_logs_in_range = AsyncMock(return_value=[meal1])

        await perform_daily_reports(bot)

        i18n = I18n("en")
        expected_text = i18n.get("daily-report-header", date=yesterday_str) + i18n.get(
            "daily-report-norm", target=2000, total=1950
        )
        bot.send_message.assert_called_once_with(chat_id=333, text=expected_text)
