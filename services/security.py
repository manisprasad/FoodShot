from dataclasses import dataclass

from loguru import logger
from redis.asyncio import Redis


@dataclass
class SecurityCheckResult:
    allowed: bool
    reason: str | None = None
    retry_after: int = 0


async def check_photo_security_limits(
    redis: Redis, user_id: int, is_admin: bool = False
) -> SecurityCheckResult:
    """Adaptive anomaly detector and sliding window rate limiter.
    
    Prevents burst spamming and automated attacks on OpenAI billing.
    """
    if is_admin:
        return SecurityCheckResult(allowed=True)

    # 1. Check if user is currently under dynamic cooldown lock
    cooldown_key = f"security:cooldown:{user_id}"
    ttl = await redis.ttl(cooldown_key)
    if ttl > 0:
        return SecurityCheckResult(
            allowed=False, reason="burst_cooldown", retry_after=ttl
        )

    # 2. Sliding window burst detection (max 3 photos in 30 seconds)
    window_key = f"security:burst_window:{user_id}"
    pipe = redis.pipeline()
    pipe.incr(window_key)
    pipe.expire(window_key, 30)
    results = await pipe.execute()
    request_count = results[0]

    if request_count > 3:
        # Trigger dynamic 5-minute cooldown lock
        await redis.setex(cooldown_key, 300, "1")
        logger.warning(
            f"Burst anomaly detected for user_id={user_id} ({request_count} requests in 30s). "
            f"Applied 5-minute dynamic cooldown lock."
        )
        return SecurityCheckResult(
            allowed=False, reason="burst_limit", retry_after=300
        )

    return SecurityCheckResult(allowed=True)
