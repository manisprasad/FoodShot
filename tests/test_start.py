from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest
from aiogram.fsm.context import FSMContext
from bot.handlers.start import cmd_start, process_start_lang
from db.models import User
from core.i18n import I18n


@pytest.mark.asyncio
async def test_cmd_start_existing_user():
    message = AsyncMock()
    message.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    user = User(id=12345, username="testuser", language="en", diabetes_mode=False)

    with patch("bot.handlers.start.crud.get_user", return_value=user):
        await cmd_start(message, session, state, i18n)
        state.clear.assert_called_once()
        message.answer.assert_called_once()
        args = message.answer.call_args[0]
        assert "How to Use FoodShot:" in args[0]


@pytest.mark.asyncio
async def test_cmd_start_new_user():
    message = AsyncMock()
    message.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    with patch("bot.handlers.start.crud.get_user", return_value=None):
        await cmd_start(message, session, state, i18n)
        state.clear.assert_called_once()
        message.answer.assert_called_once_with(
            "🌍 Select your language / Оберіть мову:", reply_markup=ANY
        )


@pytest.mark.asyncio
async def test_process_start_lang_new_user():
    callback = AsyncMock()
    callback.data = "start_lang:uk"
    callback.from_user.id = 12345
    callback.from_user.username = "testuser"
    session = AsyncMock()
    i18n = I18n("en")

    with (
        patch("bot.handlers.start.crud.get_user", return_value=None),
        patch("bot.handlers.start.crud.create_user") as mock_create,
    ):
        await process_start_lang(callback, session, i18n)

        mock_create.assert_called_once_with(
            session=session,
            id=12345,
            username="testuser",
            icr=None,
            isf=None,
            target_bg=None,
            language="uk",
            diabetes_mode=False,
        )
        assert i18n.lang == "uk"
        callback.message.delete.assert_called_once()
        callback.message.answer.assert_called_once()
        args = callback.message.answer.call_args[0]
        assert "Як користуватися FoodShot:" in args[0]
        callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_start_lang_existing_user():
    callback = AsyncMock()
    callback.data = "start_lang:uk"
    callback.from_user.id = 12345
    session = AsyncMock()
    i18n = I18n("en")

    user = MagicMock()
    user.id = 12345
    user.language = "en"

    with (
        patch("bot.handlers.start.crud.get_user", return_value=user),
        patch("bot.handlers.start.crud.update_user_language") as mock_update,
    ):
        await process_start_lang(callback, session, i18n)

        mock_update.assert_called_once_with(session, 12345, "uk")
        assert i18n.lang == "uk"
        callback.message.delete.assert_called_once()
        callback.message.answer.assert_called_once()
        callback.answer.assert_called_once()
