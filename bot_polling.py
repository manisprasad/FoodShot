import asyncio
from loguru import logger
from api.webhook import dp, bot
from services.retention import run_retention_scheduler
from core.logger import setup_logging


async def main():
    setup_logging()
    logger.info("Starting bot in polling mode (24/7 Background Worker)...")

    # Ensure no webhook is active, otherwise polling will fail
    await bot.delete_webhook(drop_pending_updates=True)

    # Start the retention scheduler in the background
    scheduler_task = asyncio.create_task(run_retention_scheduler(bot))

    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
