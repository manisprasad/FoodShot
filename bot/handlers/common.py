import asyncio

from aiogram import Bot, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from core.config import config
from core.i18n import I18n
from core.redis_client import redis_client
from services.broadcast import run_broadcast

router = Router()


async def get_admin_keyboard(i18n: I18n) -> types.InlineKeyboardMarkup:
    debug_enabled = (await redis_client.get("admin:debug_mode")) == "1"
    debug_status = "🟢 ON" if debug_enabled else "🔴 OFF"

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=i18n.get("btn-admin-broadcast"),
            callback_data="admin_confirm_broadcast",
        )
    )
    builder.add(
        InlineKeyboardButton(
            text=f"🐞 Debug Info: {debug_status}",
            callback_data="admin_toggle_debug",
        )
    )
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, i18n: I18n):
    if not config.ADMIN_ID or message.from_user.id != config.ADMIN_ID:
        return

    kb = await get_admin_keyboard(i18n)
    await message.answer(
        i18n.get("admin-menu-header"),
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data == "back_to_admin")
async def process_back_to_admin(callback: types.CallbackQuery, i18n: I18n):
    if not config.ADMIN_ID or callback.from_user.id != config.ADMIN_ID:
        return

    kb = await get_admin_keyboard(i18n)
    await callback.message.edit_text(
        i18n.get("admin-menu-header"),
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data == "admin_toggle_debug")
async def process_toggle_debug(callback: types.CallbackQuery, i18n: I18n):
    if not config.ADMIN_ID or callback.from_user.id != config.ADMIN_ID:
        return

    current = (await redis_client.get("admin:debug_mode")) == "1"
    new_state = "0" if current else "1"
    await redis_client.set("admin:debug_mode", new_state)

    debug_enabled = new_state == "1"
    kb = await get_admin_keyboard(i18n)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(f"Debug mode: {'ON' if debug_enabled else 'OFF'}")


@router.callback_query(lambda c: c.data == "admin_confirm_broadcast")
async def process_confirm_broadcast(callback: types.CallbackQuery, i18n: I18n):
    if not config.ADMIN_ID or callback.from_user.id != config.ADMIN_ID:
        return

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=i18n.get("btn-admin-confirm-yes"),
            callback_data="admin_run_broadcast",
        )
    )
    builder.add(
        InlineKeyboardButton(
            text=i18n.get("btn-admin-confirm-no"), callback_data="back_to_admin"
        )
    )
    builder.adjust(2)

    await callback.message.edit_text(
        i18n.get("admin-confirm-header"),
        reply_markup=builder.as_markup(),
    )


@router.callback_query(lambda c: c.data == "admin_run_broadcast")
async def process_run_broadcast(callback: types.CallbackQuery, bot: Bot, i18n: I18n):
    if not config.ADMIN_ID or callback.from_user.id != config.ADMIN_ID:
        return

    await callback.message.edit_text(i18n.get("admin-run-success"))
    asyncio.create_task(run_broadcast(bot, callback.message.chat.id, i18n))


@router.errors()
async def global_error_handler(event: ErrorEvent, i18n: I18n = None):
    logger.exception(
        "Unhandled exception during update processing", exc_info=event.exception
    )

    if not i18n:
        i18n = I18n("en")

    update = event.update
    message = None
    if update.message:
        message = update.message
    elif update.callback_query:
        message = update.callback_query.message

    if message:
        try:
            await message.answer(i18n.get("service-unavailable"))
        except Exception as e:
            logger.error(f"Failed to send error notification to user: {e}")


@router.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext, i18n: I18n):
    await state.clear()
    await message.answer(i18n.get("menu-main"))
