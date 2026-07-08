import asyncio
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks

from sqlalchemy import text
from bot.handlers import common, history, photo, settings, start, export
from bot.i18n_middleware import SimpleI18nMiddleware
from bot.middlewares import DbSessionMiddleware
from core.config import config
from core.redis_client import redis_client
from db.database import SessionLocal
from core.logger import setup_logging
from loguru import logger
from services.retention import run_retention_scheduler
from services.keep_alive import ping_render

setup_logging()

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
storage = RedisStorage.from_url(config.REDIS_URL)
dp = Dispatcher(storage=storage)

dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))
dp.update.middleware(SimpleI18nMiddleware())

dp.include_router(common.router)
dp.include_router(history.router)
dp.include_router(settings.router)
dp.include_router(start.router)
dp.include_router(photo.router)
dp.include_router(export.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Setting Telegram webhook to %s", config.WEBHOOK_URL)
    await bot.set_webhook(
        url=config.WEBHOOK_URL, secret_token=config.WEBHOOK_SECRET_TOKEN
    )
    scheduler_task = asyncio.create_task(run_retention_scheduler(bot))
    ping_task = asyncio.create_task(ping_render())
    yield
    scheduler_task.cancel()
    ping_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    try:
        await ping_task
    except asyncio.CancelledError:
        pass
    # We purposefully do not delete the webhook here because during rolling updates
    # (like on Render), the old instance shutting down would delete the webhook
    # that the new instance just set.


async def process_update_with_timeout(
    dp: Dispatcher, bot: Bot, update: types.Update, timeout: float = 120.0
):
    try:
        await asyncio.wait_for(dp.feed_update(bot, update), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(
            "Processing of update %s timed out after %s seconds",
            update.update_id,
            timeout,
        )
    except Exception as e:
        logger.exception("Error processing update %s: %s", update.update_id, e)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        await redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@app.post("/webhook")
@app.post("/webhook/webhook")
async def telegram_webhook(
    update: dict,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(default=None),
):
    if x_telegram_bot_api_secret_token != config.WEBHOOK_SECRET_TOKEN:
        logger.warning("Invalid webhook secret token received")
        raise HTTPException(status_code=401, detail="Invalid secret token")

    telegram_update = types.Update(**update)

    update_id = update.get("update_id")
    if update_id is not None:
        cache_key = f"processed_update:{update_id}"
        try:
            is_new = await redis_client.set(cache_key, "processing", ex=120, nx=True)
            if not is_new:
                logger.info("Update %s already processing or processed", update_id)
                return {"status": "ok"}
        except Exception as e:
            logger.warning("Redis is unavailable for idempotency: %s", e)

    background_tasks.add_task(process_update_with_timeout, dp, bot, telegram_update)
    return {"status": "ok"}
