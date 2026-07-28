from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import ReplyKeyboardRemove

from bot.handlers.settings import (
    cmd_danger,
    process_back_to_settings,
    process_delete_account,
    process_delete_confirm,
)
from bot.states import Settings as SettingsState
from core.i18n import I18n


@pytest.mark.asyncio
async def test_cmd_danger():
    message = AsyncMock()
    message.from_user.id = 12345
    state = AsyncMock()
    i18n = I18n("en")

    await cmd_danger(message, state, i18n)

    state.clear.assert_called_once()
    message.answer.assert_called_once()
    assert message.answer.call_args[0][0] == i18n.get("security-zone-main")


@pytest.mark.asyncio
async def test_process_back_to_settings():
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    callback.from_user.id = 12345
    session = MagicMock()
    state = MagicMock()
    state.clear = AsyncMock()
    i18n = I18n("en")

    await process_back_to_settings(callback, session, state, i18n)

    callback.message.edit_text.assert_called_once()
    state.clear.assert_called_once()
    callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_delete_account_with_username():
    callback = AsyncMock()
    callback.from_user.id = 12345
    callback.from_user.username = "testuser"
    session = AsyncMock()
    state = AsyncMock()
    i18n = I18n("en")

    await process_delete_account(callback, session, state, i18n)

    state.set_state.assert_called_once_with(SettingsState.waiting_for_delete_confirm)
    state.update_data.assert_called_once_with(delete_target="testuser")
    callback.message.edit_reply_markup.assert_called_once_with(reply_markup=None)
    callback.message.answer.assert_called_once_with(
        i18n.get("prompt-delete-confirm", username="testuser")
    )
    callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_delete_account_no_username():
    callback = AsyncMock()
    callback.from_user.id = 12345
    callback.from_user.username = None
    callback.from_user.first_name = "Alex"
    session = AsyncMock()
    state = AsyncMock()
    i18n = I18n("en")

    await process_delete_account(callback, session, state, i18n)

    state.set_state.assert_called_once_with(SettingsState.waiting_for_delete_confirm)
    state.update_data.assert_called_once_with(delete_target="Alex")
    callback.message.edit_reply_markup.assert_called_once_with(reply_markup=None)
    callback.message.answer.assert_called_once_with(
        i18n.get("prompt-delete-confirm-no-username", first_name="Alex")
    )
    callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_delete_confirm_success():
    message = AsyncMock()
    message.from_user.id = 12345
    message.text = "testuser"
    session = AsyncMock()
    state = AsyncMock()
    state.get_data.return_value = {"delete_target": "testuser"}
    i18n = I18n("en")

    with (
        patch("bot.handlers.settings.crud.delete_user") as mock_delete_user,
        patch("bot.handlers.start.cmd_start") as mock_cmd_start,
    ):
        await process_delete_confirm(message, session, state, i18n)

        mock_delete_user.assert_called_once_with(session, 12345)
        state.clear.assert_called_once()
        message.answer.assert_called_once_with(
            i18n.get("delete-success"), reply_markup=ReplyKeyboardRemove()
        )
        mock_cmd_start.assert_called_once_with(message, session, state, i18n)


@pytest.mark.asyncio
async def test_process_delete_confirm_cancelled():
    message = AsyncMock()
    message.from_user.id = 12345
    message.text = "wronguser"
    session = AsyncMock()
    state = AsyncMock()
    state.get_data.return_value = {"delete_target": "testuser"}
    i18n = I18n("en")

    user = MagicMock()
    user.language = "en"
    user.icr = 5.0
    user.isf = 5.0
    user.target_bg = 5.0
    user.insulin_type = "NovoRapid"

    with (
        patch("bot.handlers.settings.crud.delete_user") as mock_delete_user,

    ):
        await process_delete_confirm(message, session, state, i18n)

        mock_delete_user.assert_not_called()
        assert state.clear.call_count == 2
        message.answer.assert_any_call(i18n.get("delete-cancelled"))
