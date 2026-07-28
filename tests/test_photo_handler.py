from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.photo import handle_photo
from core.i18n import I18n
from services.photo_flow import PhotoFlowResult


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
        patch("bot.handlers.photo.crud.get_user", AsyncMock(return_value=user)),
        patch(
            "bot.handlers.photo.photo_flow.execute_photo_analysis",
            AsyncMock(
                return_value=PhotoFlowResult(
                    success=False,
                    error_key="not-found",
                )
            ),
        ),
    ):
        await handle_photo(message, bot, session, state, i18n)

        # Should log and edit status message to not-found
        status_msg.edit_text.assert_called_once_with(i18n.get("not-found"))
