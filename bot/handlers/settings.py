from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import language_menu, main_menu
from bot.states import Settings as SettingsState
from bot.states import Registration as DiabetesSetupState
from core.i18n import I18n
from db import crud

router = Router()


def get_settings_keyboard(i18n: I18n) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-change-lang"), callback_data="change_lang"
        ),
        types.InlineKeyboardButton(
            text=i18n.get("btn-diabetes-mode"), callback_data="diabetes_menu"
        ),
    )
    return builder.as_markup()


@router.message(Command("settings"))
@router.message(F.text.in_({"⚙️ Settings", "⚙️ Налаштування"}))
async def cmd_settings(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    user = await crud.get_user(session, message.from_user.id)

    await message.answer(
        i18n.get(
            "settings-main",
            lang="English" if user.language == "en" else "Українська",
        ),
        reply_markup=get_settings_keyboard(i18n),
    )


@router.message(Command("danger"))
async def cmd_danger(message: types.Message, state: FSMContext, i18n: I18n):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-delete-account"), callback_data="delete_account"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-back"), callback_data="back_to_settings"
        )
    )
    await message.answer(
        i18n.get("security-zone-main"),
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "back_to_settings")
async def process_back_to_settings(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    user = await crud.get_user(session, callback.from_user.id)
    await callback.message.edit_text(
        i18n.get(
            "settings-main",
            lang="English" if user.language == "en" else "Українська",
        ),
        reply_markup=get_settings_keyboard(i18n),
    )
    await callback.answer()


@router.callback_query(F.data == "delete_account")
async def process_delete_account(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.set_state(SettingsState.waiting_for_delete_confirm)
    username = callback.from_user.username
    if username:
        await state.update_data(delete_target=username)
        prompt = i18n.get("prompt-delete-confirm", username=username)
    else:
        first_name = callback.from_user.first_name or "DELETE"
        await state.update_data(delete_target=first_name)
        prompt = i18n.get("prompt-delete-confirm-no-username", first_name=first_name)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(prompt)
    await callback.answer()


@router.message(SettingsState.waiting_for_delete_confirm, F.text)
async def process_delete_confirm(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    data = await state.get_data()
    target = data.get("delete_target")
    entered = message.text.strip().lstrip("@")

    if entered.lower() == target.lower():
        await crud.delete_user(session, message.from_user.id)
        await state.clear()
        await message.answer(
            i18n.get("delete-success"), reply_markup=types.ReplyKeyboardRemove()
        )
        from bot.handlers.start import cmd_start

        await cmd_start(message, session, state, i18n)
    else:
        await state.clear()
        await message.answer(i18n.get("delete-cancelled"))
        await cmd_settings(message, session, state, i18n)


@router.callback_query(F.data == "diabetes_menu")
async def process_diabetes_menu(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    user = await crud.get_user(session, callback.from_user.id)
    builder = InlineKeyboardBuilder()

    if not user.diabetes_mode:
        text = i18n.get("diabetes-menu-disabled")
        builder.row(
            types.InlineKeyboardButton(
                text=i18n.get("btn-enable-configure"),
                callback_data="configure_diabetes",
            )
        )
    else:
        text = i18n.get(
            "diabetes-menu-enabled",
            icr=user.icr,
            isf=user.isf,
            target=user.target_bg,
            type=user.insulin_type,
        )
        builder.row(
            types.InlineKeyboardButton(
                text=i18n.get("btn-edit-params"), callback_data="edit_diabetes_params"
            ),
            types.InlineKeyboardButton(
                text=i18n.get("btn-reconfigure-all"), callback_data="configure_diabetes"
            ),
        )
        builder.row(
            types.InlineKeyboardButton(
                text=i18n.get("btn-disable"), callback_data="disable_diabetes"
            )
        )

    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-back"), callback_data="back_to_settings"
        )
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "disable_diabetes")
async def process_disable_diabetes(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await crud.update_user(
        session,
        callback.from_user.id,
        diabetes_mode=False,
    )
    await callback.answer(i18n.get("diabetes-disabled"))
    await process_diabetes_menu(callback, session, state, i18n)


@router.callback_query(F.data == "edit_diabetes_params")
async def process_edit_diabetes_params(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18n
):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-edit-icr"), callback_data="edit:icr"
        ),
        types.InlineKeyboardButton(
            text=i18n.get("btn-edit-isf"), callback_data="edit:isf"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-edit-target_bg"), callback_data="edit:target_bg"
        ),
        types.InlineKeyboardButton(
            text=i18n.get("btn-edit-insulin_type"), callback_data="edit:insulin_type"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-back"), callback_data="diabetes_menu"
        )
    )

    await callback.message.edit_text(
        text=i18n.get("edit-params-menu"),
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit:"))
async def process_edit_field(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18n
):
    field = callback.data.split(":")[1]
    await state.set_state(SettingsState.waiting_for_value)
    await state.update_data(edit_field=field)

    prompt_key = f"prompt-edit-{field}"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-cancel"), callback_data="edit_diabetes_params"
        )
    )

    await callback.message.edit_text(
        text=i18n.get(prompt_key),
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.message(SettingsState.waiting_for_value, F.text)
async def process_new_value(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    data = await state.get_data()
    field = data.get("edit_field")

    value = message.text
    if field in ["icr", "isf", "target_bg"]:
        try:
            value = float(value.replace(",", "."))
        except ValueError:
            return await message.answer(i18n.get("error-number"))

        if field == "icr" and not (1.0 <= value <= 100.0):
            return await message.answer(i18n.get("error-range-icr"))
        elif field == "isf" and not (0.1 <= value <= 20.0):
            return await message.answer(i18n.get("error-range-isf"))
        elif field == "target_bg" and not (3.0 <= value <= 12.0):
            return await message.answer(i18n.get("error-range-target"))

    await crud.update_user(session, message.from_user.id, **{field: value})
    await state.clear()

    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(i18n.get("profile-updated"))
    await cmd_settings(message, session, state, i18n)


@router.callback_query(F.data == "configure_diabetes")
async def process_configure_diabetes(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18n
):
    await state.set_state(DiabetesSetupState.waiting_for_icr)
    await callback.message.edit_text(
        text=i18n.get("enter-icr"),
        reply_markup=None,
    )
    await callback.answer()


@router.message(DiabetesSetupState.waiting_for_icr, F.text)
async def process_setup_icr(message: types.Message, state: FSMContext, i18n: I18n):
    try:
        icr = float(message.text.replace(",", "."))
        if not (1.0 <= icr <= 100.0):
            return await message.answer(i18n.get("error-range-icr"))
        await state.update_data(icr=icr)
        await state.set_state(DiabetesSetupState.waiting_for_isf)
        await message.answer(i18n.get("enter-isf"))
    except ValueError:
        await message.answer(i18n.get("error-number"))


@router.message(DiabetesSetupState.waiting_for_isf, F.text)
async def process_setup_isf(message: types.Message, state: FSMContext, i18n: I18n):
    try:
        isf = float(message.text.replace(",", "."))
        if not (0.1 <= isf <= 20.0):
            return await message.answer(i18n.get("error-range-isf"))
        await state.update_data(isf=isf)
        await state.set_state(DiabetesSetupState.waiting_for_target_bg)
        await message.answer(i18n.get("enter-target"))
    except ValueError:
        await message.answer(i18n.get("error-number"))


@router.message(DiabetesSetupState.waiting_for_target_bg, F.text)
async def process_setup_target_bg(
    message: types.Message, state: FSMContext, i18n: I18n
):
    try:
        target_bg = float(message.text.replace(",", "."))
        if not (3.0 <= target_bg <= 12.0):
            return await message.answer(i18n.get("error-range-target"))
        await state.update_data(target_bg=target_bg)
        await state.set_state(DiabetesSetupState.waiting_for_insulin_type)
        await message.answer(i18n.get("enter-insulin"))
    except ValueError:
        await message.answer(i18n.get("error-number"))


@router.message(DiabetesSetupState.waiting_for_insulin_type, F.text)
async def process_setup_insulin_type(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    data = await state.get_data()

    await crud.update_user(
        session=session,
        user_id=message.from_user.id,
        icr=data["icr"],
        isf=data["isf"],
        target_bg=data["target_bg"],
        insulin_type=message.text,
        diabetes_mode=True,
    )
    await state.clear()

    await message.answer(
        text=i18n.get("diabetes-enabled"), reply_markup=main_menu(i18n)
    )
    await cmd_settings(message, session, state, i18n)


@router.callback_query(F.data == "change_lang")
async def process_change_lang(
    callback: types.CallbackQuery, session: AsyncSession, i18n: I18n
):
    user = await crud.get_user(session, callback.from_user.id)
    await callback.message.edit_text(
        i18n.get("select-lang"), reply_markup=language_menu(user.language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_lang:"))
async def process_set_lang(
    callback: types.CallbackQuery, session: AsyncSession, i18n: I18n
):
    new_lang = callback.data.split(":")[1]
    user = await crud.get_user(session, callback.from_user.id)

    if user.language != new_lang:
        await crud.update_user_language(session, user.id, new_lang)
        i18n.lang = new_lang

        await callback.message.answer(
            i18n.get("lang-changed"), reply_markup=main_menu(i18n)
        )

    await callback.message.delete()
    await callback.answer()
