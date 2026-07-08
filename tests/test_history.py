from datetime import datetime
from unittest.mock import AsyncMock, patch
import pytest
from aiogram.fsm.context import FSMContext
from bot.handlers.history import cmd_history, process_delete_history_by_index
from db.models import MealLog
from core.i18n import I18n


@pytest.mark.asyncio
async def test_cmd_history_empty():
    message = AsyncMock()
    message.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    with patch("bot.handlers.history.crud.get_user_history", return_value=[]):
        await cmd_history(message, session, state, i18n)
        state.clear.assert_called_once()
        message.answer.assert_called_once_with(i18n.get("history-empty"))


@pytest.mark.asyncio
async def test_cmd_history_with_meals():
    message = AsyncMock()
    message.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    log1 = MealLog(
        id=1,
        user_id=12345,
        dish_name="Chicken",
        portion_g=200.0,
        kcal=400.0,
        carbs_g=10.0,
        protein_g=40.0,
        fat_g=10.0,
        bolus_dose=None,
        created_at=datetime.now(),
    )

    with patch("bot.handlers.history.crud.get_user_history", return_value=[log1]):
        await cmd_history(message, session, state, i18n)
        state.clear.assert_called_once()
        message.answer.assert_called_once()
        args = message.answer.call_args[0]
        assert "Chicken" in args[0]
        state.set_state.assert_called_once()
        state.update_data.assert_called_once_with(meal_ids=[1])


@pytest.mark.asyncio
async def test_process_delete_history_by_index():
    message = AsyncMock()
    message.text = "1"
    message.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"meal_ids": [42]}
    i18n = I18n("en")

    log1 = MealLog(
        id=1,
        user_id=12345,
        dish_name="Salad",
        portion_g=100.0,
        kcal=100.0,
        carbs_g=5.0,
        protein_g=2.0,
        fat_g=5.0,
        bolus_dose=None,
        created_at=datetime.now(),
    )

    with (
        patch("bot.handlers.history.crud.delete_meal_log") as mock_delete,
        patch(
            "bot.handlers.history.crud.get_user_history", return_value=[log1]
        ) as mock_get,
    ):
        await process_delete_history_by_index(message, session, state, i18n)

        mock_delete.assert_called_once_with(session, 42)
        mock_get.assert_called_once_with(session, 12345, limit=10)
        assert message.answer.call_count == 2
        message.answer.assert_any_call(i18n.get("meal-deleted"))
        state.update_data.assert_called_once_with(meal_ids=[1])
