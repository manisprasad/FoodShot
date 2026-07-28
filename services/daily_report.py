import asyncio
import re
from datetime import time, timedelta

from aiogram import Bot
from loguru import logger

from core import time_utils
from core.i18n import I18n
from core.redis_client import redis_client
from db import crud
from db.database import SessionLocal


def parse_time_string(text: str) -> time | None:
    text = text.strip()

    # Normalize separators (. , ; / spaces) to :
    normalized = re.sub(r"[\s.,;/]+", ":", text)

    # Handle "1200" format
    if len(normalized) == 4 and normalized.isdigit():
        normalized = f"{normalized[:2]}:{normalized[2:]}"
    # Handle "12" format (hour only)
    elif len(normalized) <= 2 and normalized.isdigit():
        normalized = f"{normalized}:00"

    match = re.match(r"^(\d{1,2}):(\d{2})$", normalized)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return time(h, m)
    return None


async def perform_daily_reports(bot: Bot):
    now = time_utils.get_local_now()
    now_time = now.time()

    async with SessionLocal() as session:
        try:
            users = await crud.get_users_for_daily_report(session)
            for user in users:
                report_time = user.daily_report_time or time(1, 0)

                # Skip if it is not yet time for this user's report
                if now_time < report_time:
                    continue

                # Determine the report date
                if report_time.hour < 4:
                    report_date = now.date() - timedelta(days=1)
                else:
                    report_date = now.date()

                report_date_str = report_date.strftime("%Y-%m-%d")
                lock_key = f"daily_report_sent:{user.id}:{report_date_str}"

                # Check if already sent
                already_sent = await redis_client.get(lock_key)
                if already_sent:
                    continue

                logger.info(
                    "Sending daily progress report to user %s for date %s...",
                    user.id,
                    report_date_str,
                )

                start_time, end_time = time_utils.get_local_day_utc_range(report_date)

                logs = await crud.get_meal_logs_in_range(
                    session, user.id, start_time, end_time
                )
                total_kcal = sum(log.kcal or 0.0 for log in logs)
                target = user.daily_calorie_target

                diff = total_kcal - target
                i18n = I18n(user.language)

                header = i18n.get("daily-report-header", date=report_date_str)
                if diff > 100:
                    body = i18n.get(
                        "daily-report-surplus",
                        target=target,
                        total=int(round(total_kcal)),
                        diff=int(round(diff)),
                    )
                elif diff < -100:
                    body = i18n.get(
                        "daily-report-deficit",
                        target=target,
                        total=int(round(total_kcal)),
                        diff=int(round(abs(diff))),
                    )
                else:
                    body = i18n.get(
                        "daily-report-norm",
                        target=target,
                        total=int(round(total_kcal)),
                    )

                message_text = f"{header}{body}"
                try:
                    await bot.send_message(chat_id=user.id, text=message_text)
                    # Mark as sent for this user for this day (expire key after 2 days)
                    await redis_client.set(lock_key, "sent", ex=172800)
                except Exception as e:
                    logger.warning(
                        "Failed to send daily report to user %s: %s", user.id, e
                    )
        except Exception as e:
            logger.exception("Error during daily progress reports: %s", e)


async def run_daily_report_scheduler(bot: Bot):
    logger.info("Daily report scheduler started.")
    while True:
        try:
            await perform_daily_reports(bot)
        except Exception as e:
            logger.exception("Error running daily report scheduler step: %s", e)
        # Sleep for 10 minutes
        await asyncio.sleep(600)
