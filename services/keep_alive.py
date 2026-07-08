import asyncio
import aiohttp
from loguru import logger
from core.config import config


async def ping_render():
    """
    Background task to ping the service's own /health endpoint every 10 minutes.
    This prevents Render's free Web Service from going to sleep due to inactivity.
    """
    if not config.WEBHOOK_URL:
        return

    # derive health url from webhook url (e.g. https://domain.com/webhook -> https://domain.com/health)
    health_url = (
        config.WEBHOOK_URL.replace("/webhook/webhook", "").replace("/webhook", "")
        + "/health"
    )

    if not health_url.startswith("http"):
        return

    logger.info(
        "Starting self-ping background task for %s (pings every 10 mins)", health_url
    )

    # Wait a bit before first ping to allow server to fully start
    await asyncio.sleep(60)

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(health_url, timeout=10) as resp:
                    logger.debug("Self-ping status: %s", resp.status)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Self-ping failed: %s", e)

            # Ping every 10 minutes (600 seconds)
            await asyncio.sleep(600)
