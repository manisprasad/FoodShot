from dataclasses import dataclass
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import config
from db import crud
from db.models import User
from services import calc, freemium, nutrition, security, vision


@dataclass
class PhotoFlowResult:
    success: bool
    error_key: str | None = None
    error_message: str | None = None
    state_data: dict[str, Any] | None = None
    weight_g: int | None = None
    last_bg: float | None = None


async def execute_photo_analysis(
    session: AsyncSession,
    user: User,
    photo_bytes: bytes,
    photo_file_id: str,
) -> PhotoFlowResult:
    """Execute photo recognition, security/freemium checks, and nutrition lookup."""
    is_admin = user.id == config.ADMIN_ID if config.ADMIN_ID else False

    # 1. Security burst protection check
    sec_check = await security.check_photo_security_limits(
        user_id=user.id, is_admin=is_admin
    )
    if not sec_check.allowed:
        return PhotoFlowResult(
            success=False,
            error_message=(
                f"⚠️ Too many requests. Please wait {sec_check.retry_after} "
                "seconds before sending another photo."
            ),
        )

    # 2. Freemium daily quota check
    quota_check = await freemium.check_daily_freemium_quota(
        user=user, is_admin=is_admin
    )
    if not quota_check.allowed:
        return PhotoFlowResult(
            success=False,
            error_message=(
                f"⭐️ You have reached your daily limit of free photo analyses "
                f"({freemium.FREE_TIER_DAILY_LIMIT}/day).\n\n"
                "Upgrade to FoodShot Premium for unlimited AI meal logging!"
            ),
        )

    # 3. Vision AI analysis
    try:
        vision_data = await vision.analyze_food_photo(
            photo_bytes, language=user.language
        )
        if not vision_data:
            return PhotoFlowResult(success=False, error_key="not-found")
    except vision.VisionAPIError as e:
        logger.error(f"Vision API error: {e}")
        return PhotoFlowResult(success=False, error_key="service-unavailable")

    dish_display = vision_data["dish_name"]
    dish_en = vision_data.get("dish_name_en", dish_display)
    weight_g = vision_data["weight_g"]
    confidence = vision_data.get("confidence", "medium")

    if weight_g <= 0:
        logger.error(f"Invalid weight_g received from Vision API: {weight_g}")
        return PhotoFlowResult(success=False, error_key="not-found")

    # 4. USDA Nutrition API lookup
    try:
        nutrition_data = await nutrition.get_nutrition_data(dish_en, weight_g)
        if not nutrition_data:
            return PhotoFlowResult(success=False, error_key="not-found")
    except nutrition.USDAAPIError as e:
        logger.error(f"Nutrition API error: {e}")
        return PhotoFlowResult(success=False, error_key="service-unavailable")

    # 5. Last BG retrieval
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
        "photo_id": photo_file_id,
        "last_bg": last_bg,
        "model_used": vision_data.get("model_used", config.DEFAULT_VISION_MODEL),
        "total_tokens": vision_data.get("total_tokens", 0),
    }

    return PhotoFlowResult(
        success=True,
        state_data=state_data,
        weight_g=weight_g,
        last_bg=last_bg,
    )


async def complete_meal_analysis(
    session: AsyncSession,
    user: User,
    data: dict[str, Any],
    current_bg_text: str | None,
) -> dict[str, Any]:
    """Calculate bolus if diabetes mode, save meal log in DB, and return macro result."""
    current_bg = None
    if user.diabetes_mode and current_bg_text and current_bg_text != "/skip":
        try:
            current_bg = float(current_bg_text.replace(",", "."))
        except ValueError:
            return {"success": False, "error_key": "error-number"}

    weight_g = data["weight_g"]
    carbs = data["carbs_per_g"] * weight_g
    kcal = int(data["kcal_per_g"] * weight_g)
    protein = data["protein_per_g"] * weight_g
    fat = data["fat_per_g"] * weight_g

    bolus_result = None
    bolus_dose = None
    if user.diabetes_mode:
        bolus_result = calc.calculate_bolus(
            carbs=carbs,
            icr=user.icr,
            isf=user.isf,
            target_bg=user.target_bg,
            current_bg=current_bg,
        )
        bolus_dose = bolus_result["total_dose"]

    await crud.create_meal_log(
        session=session,
        user_id=user.id,
        dish_name=data["dish_name"],
        portion_g=weight_g,
        carbs_g=carbs,
        kcal=kcal,
        protein_g=protein,
        fat_g=fat,
        bolus_dose=bolus_dose,
        current_bg=current_bg,
        photo_file_id=data["photo_id"],
    )

    return {
        "success": True,
        "carbs": carbs,
        "kcal": kcal,
        "protein": protein,
        "fat": fat,
        "weight_g": weight_g,
        "bolus": bolus_result,
    }
