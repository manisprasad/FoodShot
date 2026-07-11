from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from bot.keyboards import main_menu
from core.i18n import I18n
from db import crud

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    user = await crud.get_user(session, message.from_user.id)
    if user:
        return await message.answer(
            i18n.get("how-to-use-text"), reply_markup=main_menu(i18n)
        )

    # Prompt for language selection on first start
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🇬🇧 English", callback_data="start_lang:en"),
        types.InlineKeyboardButton(text="🇺🇦 Українська", callback_data="start_lang:uk"),
    )
    await message.answer(
        "🌍 Select your language / Оберіть мову:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("start_lang:"))
async def process_start_lang(
    callback: types.CallbackQuery, session: AsyncSession, i18n: I18n
):
    lang = callback.data.split(":")[1]

    # Register user in DB safely checking if they already exist to handle double-clicks
    user = await crud.get_user(session, callback.from_user.id)
    if not user:
        try:
            await crud.create_user(
                session=session,
                id=callback.from_user.id,
                username=callback.from_user.username,
                icr=None,
                isf=None,
                target_bg=None,
                language=lang,
                diabetes_mode=False,
            )
        except Exception as e:
            logger.exception(
                "Failed to create user during start registration", exc_info=e
            )
    else:
        if user.language != lang:
            await crud.update_user_language(session, user.id, lang)

    i18n.lang = lang

    # Clean up selection message
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Send welcoming guide with the main menu reply keyboard
    await callback.message.answer(
        i18n.get("how-to-use-text"),
        reply_markup=main_menu(i18n),
    )
    await callback.answer()
