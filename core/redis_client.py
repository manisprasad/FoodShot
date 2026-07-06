import redis.asyncio as redis
from core.config import config

# Global Redis client for caching and application state
redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
