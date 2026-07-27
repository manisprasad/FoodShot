from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import weight_adjust_keyboard
from bot.states import FoodAnalysis
from core.config import config
from core.i18n import I18n
from core.redis_client import redis_client
from db import crud
from services import calc, freemium, nutrition, security, vision

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

    is_admin = user.id == config.ADMIN_ID if config.ADMIN_ID else False

    # 1. Security burst protection check
    sec_check = await security.check_photo_security_limits(
        user_id=user.id, is_admin=is_admin
    )
    if not sec_check.allowed:
        return await message.answer(
            f"⚠️ Too many requests. Please wait {sec_check.retry_after} seconds before sending another photo."
        )

    # 2. Freemium daily quota check
    quota_check = await freemium.check_daily_freemium_quota(
        user=user, is_admin=is_admin
    )
    if not quota_check.allowed:
        return await message.answer(
            f"⭐️ You have reached your daily limit of free photo analyses ({freemium.FREE_TIER_DAILY_LIMIT}/day).\n\n"
            f"Upgrade to FoodShot Premium for unlimited AI meal logging!"
        )

    status_msg = await message.answer(i18n.get("analyzing"))

    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    photo_bytes = await bot.download_file(photo_file.file_path)

    try:
        vision_data = await vision.analyze_food_photo(
            photo_bytes.read(), language=user.language
        )
        if not vision_data:
            return await status_msg.edit_text(i18n.get("not-found"))
    except vision.VisionAPIError as e:
        logger.error(f"Vision API error: {e}")
        return await status_msg.edit_text(i18n.get("service-unavailable"))

    dish_display = vision_data["dish_name"]
    dish_en = vision_data.get("dish_name_en", dish_display)
    weight_g = vision_data["weight_g"]
    confidence = vision_data.get("confidence", "medium")

    if weight_g <= 0:
        logger.error(f"Invalid weight_g received from Vision API: {weight_g}")
        return await status_msg.edit_text(i18n.get("not-found"))

    try:
        nutrition_data = await nutrition.get_nutrition_data(dish_en, weight_g)
        if not nutrition_data:
            return await status_msg.edit_text(i18n.get("not-found"))
    except nutrition.USDAAPIError as e:
        logger.error(f"Nutrition API error: {e}")
        return await status_msg.edit_text(i18n.get("service-unavailable"))

    last_bg = None
    if user.diabetes_mode:
        history = await crud.get_user_history(session, user.id, limit=1)
        last_bg = (
            history[0].current_bg
            if history and history[0].current_bg is not None
            else None
        )

    state_data = {
        "dish_name": dish_display,
        "dish_en": dish_en,
        "weight_g": weight_g,
        "carbs_per_g": nutrition_data["carbs"] / weight_g,
        "protein_per_g": nutrition_data["protein"] / weight_g,
        "fat_per_g": nutrition_data["fat"] / weight_g,
        "kcal_per_g": nutrition_data["kcal"] / weight_g,
        "confidence": confidence,
        "photo_id": photo.file_id,
        "last_bg": last_bg,
        "model_used": vision_data.get("model_used", config.DEFAULT_VISION_MODEL),
        "total_tokens": vision_data.get("total_tokens", 0),
    }
    await state.update_data(**state_data)
    await state.set_state(FoodAnalysis.waiting_for_bg)

    show_debug = (await redis_client.get("admin:debug_mode")) == "1"

    await status_msg.edit_text(
        _ask_bg_text(i18n, state_data, user.diabetes_mode, show_debug=show_debug),
        reply_markup=weight_adjust_keyboard(weight_g, i18n, last_bg),
    )


async def _finish_analysis(
    answer_func, user, data, current_bg_text, session, state, i18n
):
    current_bg = None
    if user.diabetes_mode and current_bg_text != "/skip":
        try:
            current_bg = float(current_bg_text.replace(",", "."))
        except ValueError:
            return await answer_func(text=i18n.get("error-number"))

    weight_g = data["weight_g"]
    carbs = data["carbs_per_g"] * weight_g
    kcal = int(data["kcal_per_g"] * weight_g)

    if user.diabetes_mode:
        bolus = calc.calculate_bolus(
            carbs=carbs,
            icr=user.icr,
            isf=user.isf,
            target_bg=user.target_bg,
            current_bg=current_bg,
        )
        bolus_dose = bolus["total_dose"]
    else:
        bolus_dose = None

    await crud.create_meal_log(
        session=session,
        user_id=user.id,
        dish_name=data["dish_name"],
        portion_g=weight_g,
        carbs_g=carbs,
        kcal=kcal,
        protein_g=data["protein_per_g"] * weight_g,
        fat_g=data["fat_per_g"] * weight_g,
        bolus_dose=bolus_dose,
        current_bg=current_bg,
        photo_file_id=data["photo_id"],
    )

    await state.clear()

    if user.diabetes_mode:
        await answer_func(
            text=i18n.get(
                "result-bolus",
                total=bolus["total_dose"],
                carb_dose=bolus["carb_dose"],
                correction=bolus["correction_dose"],
                dish=data["dish_name"],
                carbs=round(carbs, 1),
                kcal=kcal,
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
                weight=int(weight_g),
                carbs=round(carbs, 1),
                kcal=kcal,
                protein=round(data["protein_per_g"] * weight_g, 1),
                fat=round(data["fat_per_g"] * weight_g, 1),
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
