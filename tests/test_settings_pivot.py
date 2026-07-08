from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest
from aiogram.fsm.context import FSMContext
from bot.handlers.settings import (
    process_diabetes_menu,
    process_disable_diabetes,
    process_edit_diabetes_params,
    process_setup_icr,
    process_setup_isf,
    process_setup_target_bg,
    process_new_value,
)
from bot.states import Registration as DiabetesSetupState
from core.i18n import I18n


@pytest.mark.asyncio
async def test_process_diabetes_menu_disabled():
    callback = AsyncMock()
    callback.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    user = MagicMock()
    user.diabetes_mode = False

    with patch("bot.handlers.settings.crud.get_user", return_value=user):
        await process_diabetes_menu(callback, session, state, i18n)

        callback.message.edit_text.assert_called_once()
        assert (
            "Diabetes Mode: Disabled" in callback.message.edit_text.call_args[1]["text"]
        )
        state.clear.assert_called_once()
        callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_diabetes_menu_enabled():
    callback = AsyncMock()
    callback.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    user = MagicMock()
    user.diabetes_mode = True
    user.icr = 5.0
    user.isf = 5.0
    user.target_bg = 5.0
    user.insulin_type = "NovoRapid"

    with patch("bot.handlers.settings.crud.get_user", return_value=user):
        await process_diabetes_menu(callback, session, state, i18n)

        callback.message.edit_text.assert_called_once()
        assert (
            "Diabetes Mode: Enabled" in callback.message.edit_text.call_args[1]["text"]
        )
        state.clear.assert_called_once()
        callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_disable_diabetes():
    callback = AsyncMock()
    callback.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    user = MagicMock()
    user.diabetes_mode = False

    with (
        patch("bot.handlers.settings.crud.update_user") as mock_update_user,
        patch("bot.handlers.settings.crud.get_user", return_value=user),
    ):
        await process_disable_diabetes(callback, session, state, i18n)

        mock_update_user.assert_called_once_with(session, 12345, diabetes_mode=False)
        assert callback.answer.call_count == 2
        callback.answer.assert_any_call(i18n.get("diabetes-disabled"))


@pytest.mark.asyncio
async def test_process_edit_diabetes_params():
    callback = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    await process_edit_diabetes_params(callback, state, i18n)

    callback.message.edit_text.assert_called_once()
    assert callback.message.edit_text.call_args[1]["text"] == i18n.get(
        "edit-params-menu"
    )
    state.clear.assert_called_once()
    callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_setup_icr_validation():
    # Test valid ICR
    message = AsyncMock()
    message.text = "5.5"
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    await process_setup_icr(message, state, i18n)
    state.update_data.assert_called_once_with(icr=5.5)
    state.set_state.assert_called_once_with(DiabetesSetupState.waiting_for_isf)
    message.answer.assert_called_once_with(i18n.get("enter-isf"))

    # Test invalid range ICR (too low)
    message_invalid = AsyncMock()
    message_invalid.text = "0.5"
    state_invalid = AsyncMock(spec=FSMContext)

    await process_setup_icr(message_invalid, state_invalid, i18n)
    state_invalid.update_data.assert_not_called()
    message_invalid.answer.assert_called_once_with(i18n.get("error-range-icr"))


@pytest.mark.asyncio
async def test_process_setup_isf_validation():
    # Test valid ISF
    message = AsyncMock()
    message.text = "4.5"
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    await process_setup_isf(message, state, i18n)
    state.update_data.assert_called_once_with(isf=4.5)
    state.set_state.assert_called_once_with(DiabetesSetupState.waiting_for_target_bg)
    message.answer.assert_called_once_with(i18n.get("enter-target"))

    # Test invalid range ISF (too high)
    message_invalid = AsyncMock()
    message_invalid.text = "25.0"
    state_invalid = AsyncMock(spec=FSMContext)

    await process_setup_isf(message_invalid, state_invalid, i18n)
    state_invalid.update_data.assert_not_called()
    message_invalid.answer.assert_called_once_with(i18n.get("error-range-isf"))


@pytest.mark.asyncio
async def test_process_setup_target_bg_validation():
    # Test valid Target BG
    message = AsyncMock()
    message.from_user.id = 12345
    message.text = "5.5"
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"icr": 5.0, "isf": 5.0}
    i18n = I18n("en")

    user = MagicMock()
    user.language = "en"

    with (
        patch("bot.handlers.settings.crud.update_user") as mock_update_user,
        patch("bot.handlers.settings.crud.get_user", return_value=user),
    ):
        await process_setup_target_bg(message, session, state, i18n)

        mock_update_user.assert_called_once_with(
            session=session,
            user_id=12345,
            icr=5.0,
            isf=5.0,
            target_bg=5.5,
            diabetes_mode=True,
        )
        assert state.clear.call_count == 2
        assert message.answer.call_count == 2
        message.answer.assert_any_call(
            text=i18n.get("diabetes-enabled"), reply_markup=ANY
        )

    # Test invalid range Target BG (too high)
    message_invalid = AsyncMock()
    message_invalid.text = "15.0"
    session_invalid = AsyncMock()
    state_invalid = AsyncMock(spec=FSMContext)

    await process_setup_target_bg(message_invalid, session_invalid, state_invalid, i18n)
    state_invalid.update_data.assert_not_called()
    message_invalid.answer.assert_called_once_with(i18n.get("error-range-target"))


@pytest.mark.asyncio
async def test_process_new_value_validation():
    # Test valid new value
    message = AsyncMock()
    message.from_user.id = 12345
    message.text = "8.0"
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"edit_field": "icr"}
    i18n = I18n("en")

    user = MagicMock()
    user.language = "en"

    with (
        patch("bot.handlers.settings.crud.update_user") as mock_update_user,
        patch("bot.handlers.settings.crud.get_user", return_value=user),
    ):
        await process_new_value(message, session, state, i18n)

        mock_update_user.assert_called_once_with(session, 12345, icr=8.0)
        assert state.clear.call_count == 2

    # Test invalid range new value
    message_invalid = AsyncMock()
    message_invalid.from_user.id = 12345
    message_invalid.text = "150.0"
    session_invalid = AsyncMock()
    state_invalid = AsyncMock(spec=FSMContext)
    state_invalid.get_data.return_value = {"edit_field": "icr"}

    with patch("bot.handlers.settings.crud.update_user") as mock_update_user_invalid:
        await process_new_value(message_invalid, session_invalid, state_invalid, i18n)

        mock_update_user_invalid.assert_not_called()
        message_invalid.answer.assert_called_once_with(i18n.get("error-range-icr"))


@pytest.mark.asyncio
async def test_process_settings_submenu():
    from bot.handlers.settings import process_settings_submenu

    callback = AsyncMock()
    callback.from_user.id = 12345
    session = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    i18n = I18n("en")

    user = MagicMock()
    user.language = "en"

    with patch("bot.handlers.settings.crud.get_user", return_value=user):
        await process_settings_submenu(callback, session, state, i18n)

        callback.message.edit_text.assert_called_once()
        assert "Your Settings:" in callback.message.edit_text.call_args[0][0]
        state.clear.assert_called_once()
        callback.answer.assert_called_once()
