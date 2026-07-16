import asyncio
import json
import os

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select

from core.i18n import I18n
from db.database import SessionLocal
from db.models import User


async def run_broadcast(bot: Bot, admin_chat_id: int, i18n: I18n):
    json_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../locales/current_update.json")
    )
    if not os.path.exists(json_path):
        await bot.send_message(admin_chat_id, i18n.get("admin-broadcast-error-missing"))
        return

    with open(json_path, encoding="utf-8") as f:
        try:
            update_data = json.load(f)
        except Exception as e:
            await bot.send_message(
                admin_chat_id,
                i18n.get("admin-broadcast-error-json", error=str(e)),
            )
            return

    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await bot.send_message(
            admin_chat_id,
            "❌ No users found in database."
            if i18n.lang == "en"
            else "❌ Не знайдено користувачів у базі даних.",
        )
        return

    await bot.send_message(
        admin_chat_id,
        i18n.get("admin-broadcast-started", count=len(users)),
    )

    success_count = 0
    fail_count = 0
    forbidden_count = 0

    for user in users:
        lang = user.language if user.language in ("en", "uk") else "en"
        text_key = f"text_{lang}"
        text = update_data.get(text_key, update_data.get("text_en", ""))

        builder = InlineKeyboardBuilder()
        buttons = update_data.get("buttons", [])
        for btn in buttons:
            btn_text = btn.get(f"text_{lang}", btn.get("text_en", ""))
            btn_callback = btn.get("callback_data")
            if btn_text and btn_callback:
                builder.add(
                    InlineKeyboardButton(text=btn_text, callback_data=btn_callback)
                )
        builder.adjust(1)

        try:
            await bot.send_message(
                chat_id=user.id,
                text=text,
                reply_markup=builder.as_markup() if buttons else None,
            )
            success_count += 1
        except TelegramForbiddenError:
            forbidden_count += 1
        except TelegramAPIError as e:
            fail_count += 1
            logger.error(f"Failed to send update to {user.id}: {e}")
        except Exception:
            fail_count += 1
            logger.exception(f"Unexpected error for user {user.id}")

        await asyncio.sleep(0.05)

    summary = i18n.get(
        "admin-broadcast-summary",
        success=success_count,
        blocked=forbidden_count,
        failed=fail_count,
    )
    await bot.send_message(admin_chat_id, summary)
