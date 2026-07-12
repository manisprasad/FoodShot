import asyncio
from datetime import datetime, time, timedelta

from aiogram import Bot
from loguru import logger

from core.i18n import I18n
from core.redis_client import redis_client
from db import crud
from db.database import SessionLocal

REDIS_REPORT_LOCK_KEY = "last_daily_report_date"


async def perform_daily_reports(bot: Bot):
    now = datetime.now()
    # Only run after 1:00 AM
    if now.hour < 1:
        return

    today_str = now.date().strftime("%Y-%m-%d")

    last_checked = await redis_client.get(REDIS_REPORT_LOCK_KEY)
    if last_checked and last_checked == today_str:
        logger.debug("Daily progress reports already sent today (%s)", today_str)
        return

    logger.info("Starting daily progress reports for %s...", today_str)

    yesterday = now.date() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    start_time = datetime.combine(yesterday, time.min)
    end_time = datetime.combine(yesterday, time.max)

    async with SessionLocal() as session:
        try:
            users = await crud.get_users_for_daily_report(session)
            for user in users:
                logs = await crud.get_meal_logs_in_range(
                    session, user.id, start_time, end_time
                )
                total_kcal = sum(log.kcal or 0.0 for log in logs)
                target = user.daily_calorie_target

                diff = total_kcal - target
                i18n = I18n(user.language)

                header = i18n.get("daily-report-header", date=yesterday_str)
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
                except Exception as e:
                    logger.warning(
                        "Failed to send daily report to user %s: %s", user.id, e
                    )

            # Mark as checked
            await redis_client.set(REDIS_REPORT_LOCK_KEY, today_str)
            logger.info("Daily progress reports completed for %s.", today_str)
        except Exception as e:
            logger.exception("Error during daily progress reports: %s", e)
            # Do not rollback the session here as the CRUD functions commit/flush individually,
            # but we catch exceptions per loop.


async def run_daily_report_scheduler(bot: Bot):
    logger.info("Daily report scheduler started.")
    while True:
        try:
            await perform_daily_reports(bot)
        except Exception as e:
            logger.exception("Error running daily report scheduler step: %s", e)
        # Sleep for 10 minutes
        await asyncio.sleep(600)
