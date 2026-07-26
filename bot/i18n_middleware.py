from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from loguru import logger

from core.i18n import I18n
from db import crud


class SimpleI18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: TelegramUser = data.get("event_from_user")
        session = data.get("session")

        lang = "en"
        if user:
            try:
                db_user = await crud.get_user(session, user.id)
                if db_user:
                    lang = db_user.language
                else:
                    lang = (
                        user.language_code
                        if user.language_code in ["uk", "en"]
                        else "en"
                    )
            except Exception as e:
                logger.exception("Failed to get user in i18n middleware", exc_info=e)
                if session:
                    await session.rollback()
                lang = (
                    user.language_code
                    if getattr(user, "language_code", "") in ["uk", "en"]
                    else "en"
                )

        data["i18n"] = I18n(lang)
        return await handler(event, data)
