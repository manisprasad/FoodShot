from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import weight_adjust_keyboard
from bot.states import FoodAnalysis
from core.i18n import I18n
from core.redis_client import redis_client
from db import crud
from services import photo_flow

router = Router()


def _ask_bg_text(
    i18n: I18n, data: dict, diabetes_mode: bool, show_debug: bool = False
) -> str:
    key = "ask-bg" if diabetes_mode else "ask-weight"
    text = i18n.get(
        key,
        dish=data["dish_name"],
        weight=data["weight_g"],
        carbs=round(data["carbs_per_g"] * data["weight_g"], 1),
        kcal=int(data["kcal_per_g"] * data["weight_g"]),
        confidence=i18n.get(f"confidence-{data['confidence']}"),
    )
    if show_debug and "model_used" in data and "total_tokens" in data:
        text += f"\n\n{data['model_used']}, {data['total_tokens']} tokens"
    return text


@router.message(F.photo)
async def handle_photo(
    message: types.Message,
    bot: Bot,
    session: AsyncSession,
    state: FSMContext,
    i18n: I18n,
):
    await state.clear()
    user = await crud.get_user(session, message.from_user.id)
    if not user:
        return await message.answer("Please /start registration first.")

    status_msg = await message.answer(i18n.get("analyzing"))

    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    photo_bytes = await bot.download_file(photo_file.file_path)

    flow_result = await photo_flow.execute_photo_analysis(
        session=session,
        user=user,
        photo_bytes=photo_bytes.read(),
        photo_file_id=photo.file_id,
    )

    if not flow_result.success:
        if flow_result.error_message:
            return await status_msg.edit_text(flow_result.error_message)
        return await status_msg.edit_text(i18n.get(flow_result.error_key))

    state_data = flow_result.state_data
    await state.update_data(**state_data)
    await state.set_state(FoodAnalysis.waiting_for_bg)

    show_debug = (await redis_client.get("admin:debug_mode")) == "1"

    await status_msg.edit_text(
        _ask_bg_text(i18n, state_data, user.diabetes_mode, show_debug=show_debug),
        reply_markup=weight_adjust_keyboard(
            flow_result.weight_g, i18n, flow_result.last_bg
        ),
    )


async def _finish_analysis(
    answer_func, user, data, current_bg_text, session, state, i18n
):
    res = await photo_flow.complete_meal_analysis(
        session=session,
        user=user,
        data=data,
        current_bg_text=current_bg_text,
    )

    if not res["success"]:
        return await answer_func(text=i18n.get(res["error_key"]))

    await state.clear()

    if user.diabetes_mode:
        bolus = res["bolus"]
        await answer_func(
            text=i18n.get(
                "result-bolus",
                total=bolus["total_dose"],
                carb_dose=bolus["carb_dose"],
                correction=bolus["correction_dose"],
                dish=data["dish_name"],
                carbs=round(res["carbs"], 1),
                kcal=res["kcal"],
                icr=user.icr,
                isf=user.isf,
                target=user.target_bg,
            )
        )
    else:
        await answer_func(
            text=i18n.get(
                "result-food-only",
                dish=data["dish_name"],
                weight=int(res["weight_g"]),
                carbs=round(res["carbs"], 1),
                kcal=res["kcal"],
                protein=round(res["protein"], 1),
                fat=round(res["fat"], 1),
            )
        )


@router.callback_query(FoodAnalysis.waiting_for_bg, F.data.startswith("weight:"))
async def process_weight_adjust(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    delta = int(callback.data.split(":")[1])
    data = await state.get_data()

    new_weight = max(10, data["weight_g"] + delta)
    await state.update_data(weight_g=new_weight)
    data["weight_g"] = new_weight

    user = await crud.get_user(session, callback.from_user.id)
    show_debug = (await redis_client.get("admin:debug_mode")) == "1"

    await callback.message.edit_text(
        _ask_bg_text(i18n, data, user.diabetes_mode, show_debug=show_debug),
        reply_markup=weight_adjust_keyboard(new_weight, i18n, data.get("last_bg")),
    )
    await callback.answer()


@router.message(FoodAnalysis.waiting_for_bg, F.text)
async def process_bg(
    message: types.Message, session: AsyncSession, state: FSMContext, i18n: I18n
):
    if message.text and message.text.startswith("/") and message.text != "/skip":
        await state.clear()
        return

    user = await crud.get_user(session, message.from_user.id)
    data = await state.get_data()

    await _finish_analysis(
        answer_func=message.answer,
        user=user,
        data=data,
        current_bg_text=message.text,
        session=session,
        state=state,
        i18n=i18n,
    )


@router.callback_query(FoodAnalysis.waiting_for_bg, F.data.startswith("bg:"))
async def process_bg_callback(
    callback: types.CallbackQuery, session: AsyncSession, state: FSMContext, i18n: I18n
):
    action = callback.data.split(":")[1]
    bg_text = "/skip" if action == "skip" else action

    user = await crud.get_user(session, callback.from_user.id)
    data = await state.get_data()

    await callback.message.edit_reply_markup(reply_markup=None)

    await _finish_analysis(
        answer_func=callback.message.answer,
        user=user,
        data=data,
        current_bg_text=bg_text,
        session=session,
        state=state,
        i18n=i18n,
    )
    await callback.answer()
