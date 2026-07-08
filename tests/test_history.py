from datetime import datetime
from unittest.mock import AsyncMock, patch
import pytest
from aiogram.fsm.context import FSMContext
from bot.handlers.history import cmd_history, process_delete_meal
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
        message.answer.assert_called_once_with(
            i18n.get("history-empty"),
            reply_markup=None,
        )


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
        kwargs = message.answer.call_args[1]
        assert "Chicken" in args[0]
        assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_process_delete_meal():
    callback = AsyncMock()
    callback.data = "delete_meal:42"
    callback.from_user.id = 12345
    session = AsyncMock()
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
        await process_delete_meal(callback, session, i18n)

        mock_delete.assert_called_once_with(session, 42)
        mock_get.assert_called_once_with(session, 12345, limit=10)
        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once_with(i18n.get("meal-deleted"))
