import asyncio
import json
import os
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import config
from db.database import SessionLocal
from db.models import User


async def main():
    json_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../locales/current_update.json")
    )
    if not os.path.exists(json_path):
        print(f"Error: current_update.json not found at {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        try:
            update_data = json.load(f)
        except Exception as e:
            print(f"Error parsing current_update.json: {e}")
            sys.exit(1)

    # Initialize bot with default parse mode as Markdown to match the webhook setup
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="Markdown"),
    )

    # Fetch all active users from database
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        print("No users found in database.")
        await bot.session.close()
        return

    print(f"Starting broadcast of release update to {len(users)} users...")
    success_count = 0
    fail_count = 0
    forbidden_count = 0

    for user in users:
        lang = user.language if user.language in ("en", "uk") else "en"
        text_key = f"text_{lang}"
        text = update_data.get(text_key, update_data.get("text_en", ""))

        # Build inline keyboard buttons with localized text
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
            print(
                f"[{success_count + fail_count + forbidden_count}/{len(users)}] Sent to user {user.id} ({user.username or 'no username'})"
            )
        except TelegramForbiddenError:
            forbidden_count += 1
            print(
                f"[{success_count + fail_count + forbidden_count}/{len(users)}] User {user.id} blocked the bot"
            )
        except TelegramAPIError as e:
            fail_count += 1
            print(
                f"[{success_count + fail_count + forbidden_count}/{len(users)}] Failed to send to user {user.id}: {e}"
            )
        except Exception as e:
            fail_count += 1
            print(
                f"[{success_count + fail_count + forbidden_count}/{len(users)}] Unexpected error for user {user.id}: {e}"
            )

        # Sleep to avoid Telegram FloodLimits (max 30 msgs/second)
        await asyncio.sleep(0.05)

    print("\nBroadcast execution finished.")
    print(f"Successfully sent: {success_count}")
    print(f"Blocked by user: {forbidden_count}")
    print(f"Failed deliveries: {fail_count}")

    await bot.session.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
