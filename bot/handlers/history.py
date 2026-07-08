from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import I18n
from db import crud
from db.models import MealLog

router = Router()


EMOJI_NUMBERS = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟",
}


def get_history_content(
    meals: list[MealLog], i18n: I18n
) -> tuple[str, types.InlineKeyboardMarkup | None]:
    if not meals:
        return i18n.get("history-empty"), None

    text = i18n.get("history-header") + "\n"
    builder = InlineKeyboardBuilder()
    row_buttons = []

    for idx, meal in enumerate(meals, 1):
        date_str = meal.created_at.strftime("%d.%m %H:%M")

        # Format meal item with or without bolus dose depending on mode
        if meal.bolus_dose is not None:
            item_text = (
                f"{idx}. 🗓 {date_str} | *{meal.dish_name}*\n"
                f"   Carbs: `{round(meal.carbs_g, 1)}g` | Dose: `{meal.bolus_dose}U`"
            )
        else:
            item_text = (
                f"{idx}. 🗓 {date_str} | *{meal.dish_name}*\n"
                f"   Carbs: `{round(meal.carbs_g, 1)}g`"
            )

        text += item_text + "\n\n"

        # Add delete button matching this list index with emoji numbers
        btn_label = EMOJI_NUMBERS.get(idx, str(idx))
        row_buttons.append(
            types.InlineKeyboardButton(
                text=btn_label, callback_data=f"delete_meal:{meal.id}"
            )
        )

    # Group delete buttons into rows of up to 5
    for i in range(0, len(row_buttons), 5):
        builder.row(*row_buttons[i : i + 5])

    return text, builder.as_markup()


@router.message(Command("history"))
@router.message(F.text.in_({"📝 Manage Last 10", "📝 Керувати останніми 10"}))
async def cmd_history(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    await state.clear()
    meals = await crud.get_user_history(session, message.from_user.id, limit=10)
    text, reply_markup = get_history_content(meals, i18n)
    await message.answer(text, reply_markup=reply_markup)


@router.callback_query(F.data.startswith("delete_meal:"))
async def process_delete_meal(
    callback: types.CallbackQuery, session: AsyncSession, i18n: I18n
):
    meal_id = int(callback.data.split(":")[1])

    # Delete meal log
    await crud.delete_meal_log(session, meal_id)

    # Re-fetch updated logs
    meals = await crud.get_user_history(session, callback.from_user.id, limit=10)
    text, reply_markup = get_history_content(meals, i18n)

    # Edit message in-place
    await callback.message.edit_text(text=text, reply_markup=reply_markup)
    await callback.answer(i18n.get("meal-deleted"))
