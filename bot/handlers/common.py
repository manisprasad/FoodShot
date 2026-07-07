from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from loguru import logger

from core.i18n import I18n

router = Router()


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
