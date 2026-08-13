import csv
import io
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from core import time_utils
from core.i18n import I18n
from db import crud

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
        1: "січень",
        2: "лютий",
        3: "березень",
        4: "квітень",
        5: "травень",
        6: "червень",
        7: "липень",
        8: "серпень",
        9: "вересень",
        10: "жовтень",
        11: "листопад",
        12: "грудень",
    },
}


def get_export_range(period: str) -> tuple[datetime, datetime]:
    now_local = time_utils.get_local_now()
    if period == "all":
        start_utc, _ = time_utils.get_local_day_utc_range(
            now_local.date() - timedelta(days=90)
        )
        end_utc = time_utils.get_utc_now()
        return start_utc, end_utc

    # Expected format: "YYYY-MM"
    year_str, month_str = period.split("-")
    year = int(year_str)
    month = int(month_str)

    start_local = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
    else:
        end_local = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)

    # Limit current month's end to current time
    if year == now_local.year and month == now_local.month:
        end_local = now_local

    return time_utils.to_utc_time(start_local), time_utils.to_utc_time(end_local)


async def get_export_keyboard(
    session: AsyncSession, user_id: int, i18n: I18n
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Fetch active months from database
    active_months = await crud.get_active_months(session, user_id)

    # Add a button for each active month
    for year, month in active_months:
        month_name = MONTH_NAMES.get(i18n.lang, MONTH_NAMES["en"]).get(month, "")
        # Capitalize for the button label
        label = f"📅 {month_name.capitalize()} {year}"
        callback_data = f"export:month:{year}-{month}"
        builder.row(types.InlineKeyboardButton(text=label, callback_data=callback_data))

    # If the user has active logs, also show "All 3 Months" option
    if active_months:
        builder.row(
            types.InlineKeyboardButton(
                text=i18n.get("btn-export-all-3"), callback_data="export:all"
            )
        )

    # Back button
    builder.row(
        types.InlineKeyboardButton(
            text=i18n.get("btn-back"), callback_data="back_to_settings"
        )
    )
    return builder.as_markup()


@router.message(Command("export"))
async def cmd_export(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    keyboard = await get_export_keyboard(session, message.from_user.id, i18n)
    await message.answer(
        i18n.get("export-choose-period"),
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "export_menu")
async def process_export_menu(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    keyboard = await get_export_keyboard(session, callback.from_user.id, i18n)
    await callback.message.edit_text(
        i18n.get("export-choose-period"),
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def process_export_action(
    callback: types.CallbackQuery, session: AsyncSession, i18n: I18n
):
    # Parse callback_data: either "export:all" or "export:month:YYYY-MM"
    parts = callback.data.split(":")
    period_type = parts[1]

    if period_type == "all":
        start_date, end_date = get_export_range("all")
        # Localized filename for "All 3 Months"
        if i18n.lang == "uk":
            filename = "щоденник-харчування-усі-3-місяці.csv"
        else:
            filename = "food-diary-all-3-months.csv"
    else:
        # period_type is "month"
        period = parts[2]  # YYYY-MM
        start_date, end_date = get_export_range(period)

        # Get localized month name and format filename
        year_str, month_str = period.split("-")
        month = int(month_str)
        month_name = MONTH_NAMES.get(i18n.lang, MONTH_NAMES["en"]).get(month, "")

        if i18n.lang == "uk":
            filename = f"щоденник-харчування-{month_name}-{year_str}.csv"
        else:
            filename = f"food-diary-{month_name.lower()}-{year_str}.csv"

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

    # Generate CSV in memory
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
        local_dt = time_utils.to_local_time(log.created_at)
        date_str = local_dt.strftime("%Y-%m-%d %H:%M:%S") if local_dt else ""
        writer.writerow(
            [
                date_str,
                log.dish_name,
                round(log.portion_g, 1) if log.portion_g is not None else "",
                log.kcal,
                round(log.carbs_g, 1) if log.carbs_g is not None else "",
                round(log.protein_g, 1) if log.protein_g is not None else "",
                round(log.fat_g, 1) if log.fat_g is not None else "",
                round(log.current_bg, 1) if log.current_bg is not None else "",
                round(log.bolus_dose, 1) if log.bolus_dose is not None else "",
            ]
        )

    csv_data = output.getvalue().encode("utf-8")
    document = types.BufferedInputFile(csv_data, filename=filename)

    # Send document directly using callback.bot.send_document to ensure reliability
    await callback.bot.send_document(chat_id=callback.from_user.id, document=document)
