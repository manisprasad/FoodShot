from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import User
from services.freemium import FreemiumQuotaResult
from services.nutrition import USDAAPIError
from services.photo_flow import complete_meal_analysis, execute_photo_analysis
from services.security import SecurityCheckResult
from services.vision import VisionAPIError


@pytest.mark.asyncio
async def test_execute_photo_analysis_success():
    session = AsyncMock()
    user = User(id=123, language="en", diabetes_mode=True)

    with (
        patch(
            "services.photo_flow.security.check_photo_security_limits",
            AsyncMock(return_value=SecurityCheckResult(allowed=True)),
        ),
        patch(
            "services.photo_flow.freemium.check_daily_freemium_quota",
            AsyncMock(
                return_value=FreemiumQuotaResult(
                    allowed=True, is_premium=False, used_today=1, daily_limit=5
                )
            ),
        ),
        patch(
            "services.photo_flow.vision.analyze_food_photo",
            AsyncMock(
                return_value={
                    "dish_name": "Grilled Chicken",
                    "dish_name_en": "Grilled Chicken",
                    "weight_g": 200,
                    "confidence": "high",
                    "model_used": "gpt-4o-mini",
                    "total_tokens": 150,
                }
            ),
        ),
        patch(
            "services.photo_flow.nutrition.get_nutrition_data",
            AsyncMock(
                return_value={"carbs": 10.0, "protein": 40.0, "fat": 5.0, "kcal": 250.0}
            ),
        ),
        patch("services.photo_flow.crud.get_user_history", AsyncMock(return_value=[])),
    ):
        result = await execute_photo_analysis(
            session=session,
            user=user,
            photo_bytes=b"dummy_bytes",
            photo_file_id="photo_123",
        )

        assert result.success is True
        assert result.weight_g == 200
        assert result.state_data["dish_name"] == "Grilled Chicken"
        assert result.state_data["carbs_per_g"] == 10.0 / 200


@pytest.mark.asyncio
async def test_execute_photo_analysis_security_blocked():
    session = AsyncMock()
    user = User(id=123, language="en", diabetes_mode=False)

    with patch(
        "services.photo_flow.security.check_photo_security_limits",
        AsyncMock(return_value=SecurityCheckResult(allowed=False, retry_after=60)),
    ):
        result = await execute_photo_analysis(
            session=session,
            user=user,
            photo_bytes=b"dummy_bytes",
            photo_file_id="photo_123",
        )

        assert result.success is False
        assert "Too many requests" in result.error_message


@pytest.mark.asyncio
async def test_execute_photo_analysis_freemium_quota_exceeded():
    session = AsyncMock()
    user = User(id=123, language="en", diabetes_mode=False)

    with (
        patch(
            "services.photo_flow.security.check_photo_security_limits",
            AsyncMock(return_value=SecurityCheckResult(allowed=True)),
        ),
        patch(
            "services.photo_flow.freemium.check_daily_freemium_quota",
            AsyncMock(
                return_value=FreemiumQuotaResult(
                    allowed=False, is_premium=False, used_today=6, daily_limit=5
                )
            ),
        ),
    ):
        result = await execute_photo_analysis(
            session=session,
            user=user,
            photo_bytes=b"dummy_bytes",
            photo_file_id="photo_123",
        )

        assert result.success is False
        assert "reached your daily limit" in result.error_message


@pytest.mark.asyncio
async def test_execute_photo_analysis_vision_error():
    session = AsyncMock()
    user = User(id=123, language="en", diabetes_mode=False)

    with (
        patch(
            "services.photo_flow.security.check_photo_security_limits",
            AsyncMock(return_value=SecurityCheckResult(allowed=True)),
        ),
        patch(
            "services.photo_flow.freemium.check_daily_freemium_quota",
            AsyncMock(
                return_value=FreemiumQuotaResult(
                    allowed=True, is_premium=False, used_today=1, daily_limit=5
                )
            ),
        ),
        patch(
            "services.photo_flow.vision.analyze_food_photo",
            AsyncMock(side_effect=VisionAPIError("OpenAI down")),
        ),
    ):
        result = await execute_photo_analysis(
            session=session,
            user=user,
            photo_bytes=b"dummy_bytes",
            photo_file_id="photo_123",
        )

        assert result.success is False
        assert result.error_key == "service-unavailable"


@pytest.mark.asyncio
async def test_execute_photo_analysis_usda_error():
    session = AsyncMock()
    user = User(id=123, language="en", diabetes_mode=False)

    with (
        patch(
            "services.photo_flow.security.check_photo_security_limits",
            AsyncMock(return_value=SecurityCheckResult(allowed=True)),
        ),
        patch(
            "services.photo_flow.freemium.check_daily_freemium_quota",
            AsyncMock(
                return_value=FreemiumQuotaResult(
                    allowed=True, is_premium=False, used_today=1, daily_limit=5
                )
            ),
        ),
        patch(
            "services.photo_flow.vision.analyze_food_photo",
            AsyncMock(
                return_value={
                    "dish_name": "Apple",
                    "dish_name_en": "Apple",
                    "weight_g": 100,
                    "confidence": "high",
                }
            ),
        ),
        patch(
            "services.photo_flow.nutrition.get_nutrition_data",
            AsyncMock(side_effect=USDAAPIError("USDA timeout")),
        ),
    ):
        result = await execute_photo_analysis(
            session=session,
            user=user,
            photo_bytes=b"dummy_bytes",
            photo_file_id="photo_123",
        )

        assert result.success is False
        assert result.error_key == "service-unavailable"


@pytest.mark.asyncio
async def test_complete_meal_analysis_success():
    session = AsyncMock()
    user = MagicMock()
    user.id = 123
    user.diabetes_mode = True
    user.icr = 10.0
    user.isf = 2.0
    user.target_bg = 5.0

    state_data = {
        "dish_name": "Pizza",
        "weight_g": 200,
        "carbs_per_g": 0.3,
        "kcal_per_g": 2.5,
        "protein_per_g": 0.1,
        "fat_per_g": 0.1,
        "photo_id": "photo_456",
    }

    with patch("services.photo_flow.crud.create_meal_log", AsyncMock()) as mock_create:
        res = await complete_meal_analysis(
            session=session,
            user=user,
            data=state_data,
            current_bg_text="7.0",
        )

        assert res["success"] is True
        assert res["carbs"] == 60.0
        assert res["bolus"]["total_dose"] == 7.0  # 6U carbs + 1U correction
        mock_create.assert_called_once()
