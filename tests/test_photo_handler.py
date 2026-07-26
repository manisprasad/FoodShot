from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.photo import handle_photo
from core.i18n import I18n
from services.freemium import FreemiumQuotaResult
from services.security import SecurityCheckResult


@pytest.mark.asyncio
async def test_handle_photo_zero_weight():
    message = AsyncMock()
    message.from_user.id = 12345
    mock_photo = MagicMock()
    mock_photo.file_id = "test_photo_id"
    message.photo = [mock_photo]

    bot = AsyncMock()
    session = AsyncMock()
    state = AsyncMock()
    i18n = I18n("en")

    user = MagicMock()
    user.id = 12345
    user.language = "en"

    status_msg = AsyncMock()
    message.answer.return_value = status_msg

    with (
        patch("bot.handlers.photo.crud.get_user", return_value=user),
        patch(
            "bot.handlers.photo.security.check_photo_security_limits",
            return_value=SecurityCheckResult(allowed=True),
        ),
        patch(
            "bot.handlers.photo.freemium.check_daily_freemium_quota",
            return_value=FreemiumQuotaResult(allowed=True, is_premium=False, used_today=1, daily_limit=5),
        ),
        patch("bot.handlers.photo.vision.analyze_food_photo") as mock_analyze,
    ):
        mock_analyze.return_value = {
            "dish_name": "Apple",
            "dish_name_en": "Apple",
            "weight_g": 0,  # Zero weight!
            "confidence": "high",
        }

        await handle_photo(message, bot, session, state, i18n)

        # Should log and edit status message to not-found
        status_msg.edit_text.assert_called_once_with(i18n.get("not-found"))
