from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import I18n
from db import crud
from db.models import MealLog
from bot.states import HistoryState

router = Router()


def get_history_content(meals: list[MealLog], i18n: I18n) -> str:
    if not meals:
        return i18n.get("history-empty")

    text = i18n.get("history-header") + "\n"

    kcal_label = i18n.get("label-kcal")
    carbs_label = i18n.get("label-carbs")
    unit_g = i18n.get("unit-grams")

    for idx, meal in enumerate(meals, 1):
        date_str = meal.created_at.strftime("%d.%m %H:%M")

        # Format meal item with or without bolus dose depending on mode
        if meal.bolus_dose is not None:
            dose_label = i18n.get("label-dose")
            unit_u = i18n.get("unit-insulin")
            item_text = (
                f"{idx}. 🗓 {date_str} | *{meal.dish_name}*\n"
                f"   {kcal_label}: `{int(meal.kcal)}` | {carbs_label}: `{round(meal.carbs_g, 1)}{unit_g}` | {dose_label}: `{meal.bolus_dose}{unit_u}`"
            )
        else:
            item_text = (
                f"{idx}. 🗓 {date_str} | *{meal.dish_name}*\n"
                f"   {kcal_label}: `{int(meal.kcal)}` | {carbs_label}: `{round(meal.carbs_g, 1)}{unit_g}`"
            )

        text += item_text + "\n\n"

    # Append deletion hint at the bottom
    text += i18n.get("history-delete-instruction")
    return text


@router.message(Command("history"))
@router.message(F.text.in_({"📝 Last 10 Meals", "📝 Останні 10 прийомів"}))
async def cmd_history(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    meals = await crud.get_user_history(session, message.from_user.id, limit=10)
    text = get_history_content(meals, i18n)

    await message.answer(text)

    if meals:
        await state.set_state(HistoryState.waiting_for_delete)
        await state.update_data(meal_ids=[meal.id for meal in meals])


@router.message(HistoryState.waiting_for_delete, F.text.regexp(r"^(10|[1-9])$"))
async def process_delete_history_by_index(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    data = await state.get_data()
    meal_ids = data.get("meal_ids", [])

    # Parse 1-indexed number to 0-indexed index
    index = int(message.text) - 1
    if index < 0 or index >= len(meal_ids):
        max_val = len(meal_ids)
        await message.answer(i18n.get("error-invalid-index", max=max_val))
        return

    meal_id = meal_ids[index]

    # Delete meal
    await crud.delete_meal_log(session, meal_id)
    await message.answer(i18n.get("meal-deleted"))

    # Re-fetch remaining meals and send the updated list as a new message
    meals = await crud.get_user_history(session, message.from_user.id, limit=10)
    text = get_history_content(meals, i18n)
    await message.answer(text)

    if meals:
        await state.update_data(meal_ids=[meal.id for meal in meals])
    else:
        await state.clear()
