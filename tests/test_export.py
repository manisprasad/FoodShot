from datetime import datetime
from unittest.mock import ANY, AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext

from bot.handlers.export import (
    cmd_export,
    get_export_range,
    process_export_action,
    process_export_menu,
)
from core import time_utils
from core.i18n import I18n
from db.models import MealLog


@pytest.mark.asyncio
async def test_cmd_export():
    message = AsyncMock()
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    with patch("bot.handlers.export.crud.get_active_months", return_value=[(2026, 7)]):
        await cmd_export(message, session, state, i18n)
        state.clear.assert_called_once()
        message.answer.assert_called_once_with(
            i18n.get("export-choose-period"),
            reply_markup=ANY,
        )


@pytest.mark.asyncio
async def test_process_export_menu():
    callback = AsyncMock()
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    with patch("bot.handlers.export.crud.get_active_months", return_value=[(2026, 7)]):
        await process_export_menu(callback, session, state, i18n)
        state.clear.assert_called_once()
        callback.message.edit_text.assert_called_once_with(
            i18n.get("export-choose-period"),
            reply_markup=ANY,
        )
        callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_export_action_empty():
    callback = AsyncMock()
    callback.data = "export:all"
    callback.from_user.id = 12345
    session = AsyncMock()
    i18n = I18n("en")

    with patch("bot.handlers.export.crud.get_meal_logs_in_range", return_value=[]):
        await process_export_action(callback, session, i18n)
        callback.answer.assert_called_once_with(
            i18n.get("export-empty"),
            show_alert=True,
        )


@pytest.mark.asyncio
async def test_process_export_action_success():
    callback = AsyncMock()
    callback.data = "export:month:2026-07"
    callback.from_user.id = 12345
    session = AsyncMock()
    i18n = I18n("en")

    log1 = MealLog(
        id=1,
        user_id=12345,
        dish_name="Test Food",
        portion_g=150.0,
        kcal=350.0,
        carbs_g=40.0,
        protein_g=15.0,
        fat_g=10.0,
        bolus_dose=3.5,
        current_bg=7.2,
        photo_file_id="photo1",
        created_at=datetime.now(),
    )

    with patch("bot.handlers.export.crud.get_meal_logs_in_range", return_value=[log1]):
        await process_export_action(callback, session, i18n)
        callback.answer.assert_called_once()
        callback.bot.send_document.assert_called_once()
        # Verify call arguments
        call_kwargs = callback.bot.send_document.call_args[1]
        assert "document" in call_kwargs
        assert call_kwargs["document"].filename == "food-diary-july-2026.csv"


def test_get_export_range():
    # Test 'all'
    start, end = get_export_range("all")
    assert (end - start).days >= 90

    # Test month YYYY-MM (returns UTC range corresponding to local month)
    start_utc, end_utc = get_export_range("2026-06")
    start_local = time_utils.to_local_time(start_utc)
    end_local = time_utils.to_local_time(end_utc)

    assert start_local.year == 2026
    assert start_local.month == 6
    assert start_local.day == 1
    assert end_local.month == 6
    assert end_local.day == 30
