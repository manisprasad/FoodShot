from dataclasses import dataclass
from datetime import datetime, timedelta

from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core import time_utils
from core.redis_client import redis_client
from db import crud
from db.models import User

FREE_TIER_DAILY_LIMIT = 5
PREMIUM_TIER_DAILY_LIMIT = 15


def is_user_premium(user: User, now: datetime | None = None) -> bool:
    """Return True if user has an active, non-expired premium subscription."""
    if not user.is_premium or user.premium_until is None:
        return False
    current = now if now is not None else time_utils.get_utc_now()
    return user.premium_until > current


@dataclass
class FreemiumQuotaResult:
    allowed: bool
    is_premium: bool
    used_today: int
    daily_limit: int


async def check_daily_freemium_quota(
    *, user: User, is_admin: bool = False, redis: Redis = redis_client
) -> FreemiumQuotaResult:
    """Check and increment daily photo analysis quota for user."""
    now = time_utils.get_utc_now()
    is_premium_active = is_user_premium(user, now)

    # Sync DB state if subscription expired
    if user.is_premium and not is_premium_active and user.premium_until and user.premium_until <= now:
        user.is_premium = False

    if is_admin:
        return FreemiumQuotaResult(
            allowed=True,
            is_premium=True,
            used_today=0,
            daily_limit=999999,
        )

    limit = PREMIUM_TIER_DAILY_LIMIT if is_premium_active else FREE_TIER_DAILY_LIMIT

    try:
        today_str = time_utils.get_today_str()
        quota_key = f"quota:freemium:{user.id}:{today_str}"

        pipe = redis.pipeline()
        pipe.incr(quota_key)
        pipe.expire(quota_key, 86400)
        results = await pipe.execute()
        used_count = int(results[0])

        if used_count > limit:
            return FreemiumQuotaResult(
                allowed=False,
                is_premium=is_premium_active,
                used_today=used_count,
                daily_limit=limit,
            )

        return FreemiumQuotaResult(
            allowed=True,
            is_premium=is_premium_active,
            used_today=used_count,
            daily_limit=limit,
        )
    except Exception as e:
        logger.warning(f"Redis freemium check failed, bypassing: {e}")
        return FreemiumQuotaResult(
            allowed=True,
            is_premium=False,
            used_today=1,
            daily_limit=FREE_TIER_DAILY_LIMIT,
        )


async def grant_user_premium(
    session: AsyncSession, user_id: int, days: float = 0, minutes: int = 0
) -> User | None:
    """Grant or extend premium subscription for a user."""
    user = await crud.get_user(session, user_id)
    if not user:
        return None

    now = time_utils.get_utc_now()
    base_time = (
        user.premium_until if (user.premium_until and user.premium_until > now) else now
    )
    user.is_premium = True
    delta = timedelta(minutes=minutes) if minutes > 0 else timedelta(days=days)
    user.premium_until = base_time + delta
    await session.commit()
    await session.refresh(user)
    return user


async def revoke_user_premium(session: AsyncSession, user_id: int) -> User | None:
    """Revoke premium subscription for a user immediately."""
    user = await crud.get_user(session, user_id)
    if not user:
        return None

    user.is_premium = False
    user.premium_until = None
    await session.commit()
    await session.refresh(user)
    return user
