from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

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
            i18n.get("already-reg"), reply_markup=main_menu(i18n)
        )

    await crud.create_user(
        session=session,
        id=message.from_user.id,
        username=message.from_user.username,
        icr=None,
        isf=None,
        target_bg=None,
        insulin_type=None,
        language=i18n.lang,
        diabetes_mode=False,
    )
    await message.answer(i18n.get("reg-complete"), reply_markup=main_menu(i18n))
