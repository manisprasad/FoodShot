from datetime import datetime
from unittest.mock import AsyncMock, patch, ANY
import pytest
from aiogram.fsm.context import FSMContext
from bot.handlers.export import (
    cmd_export,
    process_export_menu,
    process_export_action,
    get_export_range,
)
from db.models import MealLog
from core.i18n import I18n


@pytest.mark.asyncio
async def test_cmd_export():
    message = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    await cmd_export(message, state, i18n)
    state.clear.assert_called_once()
    message.answer.assert_called_once_with(
        i18n.get("export-choose-period"),
        reply_markup=ANY,
    )


@pytest.mark.asyncio
async def test_process_export_menu():
    callback = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    await process_export_menu(callback, state, i18n)
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
    callback.data = "export:all"
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
        callback.message.reply_document.assert_called_once()
        # Verify call arguments
        call_kwargs = callback.message.reply_document.call_args[1]
        assert "document" in call_kwargs
        assert call_kwargs["document"].filename == i18n.get(
            "export-filename", period="all"
        )


def test_get_export_range():
    # Test 'all'
    start, end = get_export_range("all")
    assert (end - start).days >= 90

    # Test indices
    start0, end0 = get_export_range("0")
    assert start0.day == 1
    assert end0 <= datetime.now()
