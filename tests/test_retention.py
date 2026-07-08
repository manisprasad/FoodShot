from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from services.retention import perform_retention_checks, REDIS_RETENTION_LOCK_KEY
from core.i18n import I18n


@pytest.mark.asyncio
async def test_perform_retention_checks_already_run():
    bot = AsyncMock()
    today_str = date.today().strftime("%Y-%m-%d")

    with patch("services.retention.redis_client") as mock_redis:
        # Mock Redis returning today's date (already run)
        mock_redis.get.return_value = today_str.encode("utf-8")

        await perform_retention_checks(bot)

        mock_redis.get.assert_called_once_with(REDIS_RETENTION_LOCK_KEY)
        # Should not call database SessionLocal
        with patch("services.retention.SessionLocal") as mock_session_local:
            await perform_retention_checks(bot)
            mock_session_local.assert_not_called()


@pytest.mark.asyncio
async def test_perform_retention_checks_runs_successfully():
    bot = AsyncMock()
    today_str = date.today().strftime("%Y-%m-%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Mock user
    user = MagicMock()
    user.id = 12345
    user.language = "en"

    with (
        patch("services.retention.redis_client") as mock_redis,
        patch("services.retention.SessionLocal") as mock_session_cls,
        patch("services.retention.crud") as mock_crud,
    ):
        # Redis says last check was yesterday
        mock_redis.get.return_value = yesterday_str.encode("utf-8")

        # Mock DB session
        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        # Mock CRUD returns
        # Users with logs 83 days ago -> [12345]
        # Users with logs 89 days ago -> [12345]
        mock_crud.get_users_with_logs_on_day = AsyncMock(side_effect=[[12345], [12345]])
        mock_crud.get_user = AsyncMock(return_value=user)
        mock_crud.delete_old_meal_logs = AsyncMock(return_value=10)  # 10 deleted logs

        await perform_retention_checks(bot)

        # Assert Redis was checked and updated
        mock_redis.get.assert_called_once_with(REDIS_RETENTION_LOCK_KEY)
        mock_redis.set.assert_called_once_with(REDIS_RETENTION_LOCK_KEY, today_str)

        # Assert warnings sent
        assert bot.send_message.call_count == 2
        bot.send_message.assert_any_call(
            chat_id=12345,
            text=I18n("en").get(
                "warning-7-days",
                date=(date.today() - timedelta(days=83)).strftime("%Y-%m-%d"),
            ),
        )
        bot.send_message.assert_any_call(
            chat_id=12345,
            text=I18n("en").get(
                "warning-1-day",
                date=(date.today() - timedelta(days=89)).strftime("%Y-%m-%d"),
            ),
        )

        # Assert deletion called
        mock_crud.delete_old_meal_logs.assert_called_once()
        mock_session.commit.assert_called_once()
