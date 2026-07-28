import asyncio
from datetime import timedelta

from aiogram import Bot
from loguru import logger

from core import time_utils
from core.i18n import I18n
from core.redis_client import redis_client
from db import crud
from db.database import SessionLocal

REDIS_RETENTION_LOCK_KEY = "last_retention_check_date"


async def perform_retention_checks(bot: Bot):
    today = time_utils.get_local_now().date()
    today_str = time_utils.get_today_str()

    last_checked = await redis_client.get(REDIS_RETENTION_LOCK_KEY)
    if last_checked and last_checked == today_str:
        logger.debug("Retention check already performed today (%s)", today_str)
        return

    logger.info("Starting daily data retention checks for %s...", today_str)

    # 83 days ago = will be 90 days in 7 days
    date_83_days_ago = today - timedelta(days=83)
    start_83, end_83 = time_utils.get_local_day_utc_range(date_83_days_ago)

    # 89 days ago = will be 90 days tomorrow
    date_89_days_ago = today - timedelta(days=89)
    start_89, end_89 = time_utils.get_local_day_utc_range(date_89_days_ago)

    # 90 days threshold in UTC
    before_90 = time_utils.get_utc_now() - timedelta(days=90)

    async with SessionLocal() as session:
        try:
            # 1. 7-day warnings
            user_ids_83 = await crud.get_users_with_logs_on_day(
                session, start_83, end_83
            )
            for user_id in user_ids_83:
                user = await crud.get_user(session, user_id)
                if user:
                    i18n = I18n(user.language)
                    target_date_str = date_83_days_ago.strftime("%Y-%m-%d")
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=i18n.get("warning-7-days", date=target_date_str),
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to send 7-day warning to %s: %s", user_id, e
                        )

            # 2. 1-day warnings
            user_ids_89 = await crud.get_users_with_logs_on_day(
                session, start_89, end_89
            )
            for user_id in user_ids_89:
                user = await crud.get_user(session, user_id)
                if user:
                    i18n = I18n(user.language)
                    target_date_str = date_89_days_ago.strftime("%Y-%m-%d")
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=i18n.get("warning-1-day", date=target_date_str),
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to send 1-day warning to %s: %s", user_id, e
                        )

            # 3. Deletion
            deleted_count = await crud.delete_old_meal_logs(session, before_90)
            await session.commit()
            logger.info("Retention check complete. Deleted %d old logs.", deleted_count)

            # Mark as checked
            await redis_client.set(REDIS_RETENTION_LOCK_KEY, today_str)
        except Exception as e:
            logger.exception("Error during retention checks: %s", e)
            await session.rollback()


async def run_retention_scheduler(bot: Bot):
    logger.info("Retention scheduler started.")
    while True:
        try:
            await perform_retention_checks(bot)
        except Exception as e:
            logger.exception("Error running retention scheduler step: %s", e)
        # Sleep for 1 hour between checks
        await asyncio.sleep(3600)
