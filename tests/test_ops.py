from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import User
from ops.actions import (
    fetch_ops_users,
    fetch_user_history,
    op_grant_premium,
    op_revoke_premium,
)


@pytest.mark.asyncio
async def test_fetch_ops_users_success():
    user = User(
        id=1001,
        username="test_op_user",
        language="en",
        diabetes_mode=True,
        is_premium=False,
        premium_until=None,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )

    mock_execute = MagicMock()
    mock_execute.all.return_value = [(user, 3)]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_execute)
    mock_session.__aenter__.return_value = mock_session

    with patch("ops.actions.SessionLocal", return_value=mock_session):
        rows = await fetch_ops_users()
        assert len(rows) == 1
        assert rows[0].id == 1001
        assert rows[0].username == "test_op_user"
        assert rows[0].total_meals == 3


@pytest.mark.asyncio
async def test_op_grant_premium_success():
    mock_user = MagicMock()
    mock_user.id = 1002

    with (
        patch(
            "ops.actions.freemium.grant_user_premium",
            AsyncMock(return_value=mock_user),
        ),
        patch("ops.actions.Bot") as mock_bot_cls,
    ):
        mock_bot = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        success = await op_grant_premium(1002, 30)
        assert success is True
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_op_revoke_premium_success():
    mock_user = MagicMock()
    mock_user.id = 1003
    mock_user.language = "en"

    with (
        patch(
            "ops.actions.freemium.revoke_user_premium",
            AsyncMock(return_value=mock_user),
        ),
        patch("ops.actions.Bot") as mock_bot_cls,
    ):
        mock_bot = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        success = await op_revoke_premium(1003)
        assert success is True
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_user_history_success():
    mock_meal = MagicMock()
    mock_meal.id = 1
    mock_meal.dish_name = "Chicken Salad"
    mock_meal.portion_g = 150.0
    mock_meal.carbs_g = 12.0
    mock_meal.kcal = 220.0
    mock_meal.bolus_dose = 1.2
    mock_meal.created_at = datetime.now(UTC).replace(tzinfo=None)

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_meal]
    mock_execute = MagicMock()
    mock_execute.scalars.return_value = mock_scalars

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_execute)
    mock_session.__aenter__.return_value = mock_session

    with patch("ops.actions.SessionLocal", return_value=mock_session):
        history = await fetch_user_history(1001)
        assert len(history) == 1
        assert history[0]["dish_name"] == "Chicken Salad"
