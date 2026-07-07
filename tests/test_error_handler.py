from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import ErrorEvent, Update

from bot.handlers.common import global_error_handler
from bot.middlewares import DbSessionMiddleware
from core.i18n import I18n


@pytest.mark.asyncio
async def test_db_session_middleware_commit_on_success():
    session = AsyncMock()
    session.__aenter__.return_value = session
    session_pool = MagicMock()
    session_pool.return_value = session

    middleware = DbSessionMiddleware(session_pool=session_pool)

    handler = AsyncMock()
    handler.return_value = "success_result"

    event = MagicMock()
    data = {}

    res = await middleware(handler, event, data)

    assert res == "success_result"
    handler.assert_called_once_with(event, data)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_db_session_middleware_rollback_on_failure():
    session = AsyncMock()
    session.__aenter__.return_value = session
    session_pool = MagicMock()
    session_pool.return_value = session

    middleware = DbSessionMiddleware(session_pool=session_pool)

    handler = AsyncMock()
    handler.side_effect = ValueError("Database constraint violation")

    event = MagicMock()
    data = {}

    with pytest.raises(ValueError, match="Database constraint violation"):
        await middleware(handler, event, data)

    handler.assert_called_once_with(event, data)
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_global_error_handler_message():
    message = AsyncMock()
    update = MagicMock(spec=Update)
    update.message = message
    update.callback_query = None

    exception = ValueError("Internal handler error")
    event = ErrorEvent(update=update, exception=exception)
    i18n = I18n("en")

    with patch("bot.handlers.common.logger") as mock_logger:
        await global_error_handler(event, i18n)
        mock_logger.exception.assert_called_once_with(
            "Unhandled exception during update processing", exc_info=exception
        )
        message.answer.assert_called_once_with(i18n.get("service-unavailable"))


@pytest.mark.asyncio
async def test_global_error_handler_callback_query():
    message = AsyncMock()
    callback_query = MagicMock()
    callback_query.message = message

    update = MagicMock(spec=Update)
    update.message = None
    update.callback_query = callback_query

    exception = ValueError("Internal handler error")
    event = ErrorEvent(update=update, exception=exception)
    i18n = I18n("uk")

    with patch("bot.handlers.common.logger") as mock_logger:
        await global_error_handler(event, i18n)
        mock_logger.exception.assert_called_once_with(
            "Unhandled exception during update processing", exc_info=exception
        )
        message.answer.assert_called_once_with(i18n.get("service-unavailable"))
