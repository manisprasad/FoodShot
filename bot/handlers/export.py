import io
import csv
from datetime import datetime, timedelta, time
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from core.i18n import I18n

router = Router()

MONTH_NAMES = {
    "en": {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    },
    "uk": {
        1: "Січень",
        2: "Лютий",
        3: "Березень",
        4: "Квітень",
        5: "Травень",
        6: "Червень",
        7: "Липень",
        8: "Серпень",
        9: "Вересень",
        10: "Жовтень",
        11: "Листопад",
        12: "Грудень",
    },
}


def get_export_range(period: str) -> tuple[datetime, datetime]:
    now = datetime.now()
    if period == "all":
        start = datetime.combine(now.date() - timedelta(days=90), time.min)
        return start, now

    period_idx = int(period)
    target_date = now
    for _ in range(period_idx):
        target_date = target_date.replace(day=1) - timedelta(days=1)

    start = datetime(target_date.year, target_date.month, 1, 0, 0, 0)
    if target_date.month == 12:
        end = datetime(target_date.year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
    else:
        end = datetime(target_date.year, target_date.month + 1, 1, 0, 0, 0) - timedelta(
            seconds=1
        )

    if period_idx == 0:
        end = now

    return start, end


def get_month_button_label(period_idx: int, i18n: I18n) -> str:
    now = datetime.now()
    target_date = now
    for _ in range(period_idx):
        target_date = target_date.replace(day=1) - timedelta(days=1)

    month_name = MONTH_NAMES.get(i18n.lang, MONTH_NAMES["en"]).get(
        target_date.month, ""
    )
    return f"📅 {month_name} {target_date.year}"


def get_export_keyboard(i18n: I18n) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Month options
    builder.row(
        types.InlineKeyboardButton(
            text=get_month_button_label(0, i18n), callback_data="export:0"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=get_month_button_label(1, i18n), callback_data="export:1"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=get_month_button_label(2, i18n), callback_data="export:2"
        )
    )
    # All 3 months
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-export-all-3"), callback_data="export:all"
        )
    )
    # Back
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-back"), callback_data="back_to_settings"
        )
    )
    return builder.as_markup()


@router.message(Command("export"))
async def cmd_export(message: types.Message, state: FSMContext, i18n: I18n):
    await state.clear()
    await message.answer(
        i18n.get("export-choose-period"),
        reply_markup=get_export_keyboard(i18n),
    )


@router.callback_query(F.data == "export_menu")
async def process_export_menu(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18n
):
    await state.clear()
    await callback.message.edit_text(
        i18n.get("export-choose-period"),
        reply_markup=get_export_keyboard(i18n),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def process_export_action(
    callback: types.CallbackQuery, session: AsyncSession, i18n: I18n
):
    period = callback.data.split(":")[1]
    start_date, end_date = get_export_range(period)

    logs = await crud.get_meal_logs_in_range(
        session=session,
        user_id=callback.from_user.id,
        start_date=start_date,
        end_date=end_date,
    )

    if not logs:
        await callback.answer(i18n.get("export-empty"), show_alert=True)
        return

    await callback.answer()

    # Generate CSV
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")

    writer.writerow(
        [
            i18n.get("csv-header-date"),
            i18n.get("csv-header-dish"),
            i18n.get("csv-header-weight"),
            i18n.get("csv-header-kcal"),
            i18n.get("csv-header-carbs"),
            i18n.get("csv-header-protein"),
            i18n.get("csv-header-fat"),
            i18n.get("csv-header-bg"),
            i18n.get("csv-header-bolus"),
        ]
    )

    for log in logs:
        writer.writerow(
            [
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                log.dish_name,
                log.portion_g,
                log.kcal,
                log.carbs_g,
                log.protein_g,
                log.fat_g,
                log.current_bg if log.current_bg is not None else "",
                log.bolus_dose if log.bolus_dose is not None else "",
            ]
        )

    csv_data = output.getvalue().encode("utf-8")

    # Format filename
    filename = i18n.get("export-filename", period=period)
    document = types.BufferedInputFile(csv_data, filename=filename)

    await callback.message.reply_document(document=document)
