from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.models import User

FREE_TIER_DAILY_LIMIT = 5


def _get_utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class FreemiumQuotaResult:
    allowed: bool
    is_premium: bool
    used_today: int
    daily_limit: int


async def check_daily_freemium_quota(
    redis: Redis, user: User, is_admin: bool = False
) -> FreemiumQuotaResult:
    """Check and increment daily photo analysis quota for user."""

    # 1. Admin or active premium users have unlimited quota
    now = _get_utc_now()
    is_premium_active = user.is_premium and (
        user.premium_until is None or user.premium_until > now
    )

    if is_admin or is_premium_active:
        return FreemiumQuotaResult(
            allowed=True,
            is_premium=True,
            used_today=0,
            daily_limit=999999,
        )

    # 2. Track daily usage in Redis
    today_str = now.strftime("%Y-%m-%d")
    quota_key = f"quota:freemium:{user.id}:{today_str}"

    pipe = redis.pipeline()
    pipe.incr(quota_key)
    pipe.expire(quota_key, 86400)  # TTL 24h
    results = await pipe.execute()
    used_count = results[0]

    if used_count > FREE_TIER_DAILY_LIMIT:
        return FreemiumQuotaResult(
            allowed=False,
            is_premium=False,
            used_today=used_count,
            daily_limit=FREE_TIER_DAILY_LIMIT,
        )

    return FreemiumQuotaResult(
        allowed=True,
        is_premium=False,
        used_today=used_count,
        daily_limit=FREE_TIER_DAILY_LIMIT,
    )


async def grant_user_premium(
    session: AsyncSession, user_id: int, days: int
) -> User | None:
    """Grant or extend premium subscription for a user."""
    user = await crud.get_user(session, user_id)
    if not user:
        return None

    now = _get_utc_now()
    base_time = user.premium_until if (user.premium_until and user.premium_until > now) else now
    user.is_premium = True
    user.premium_until = base_time + timedelta(days=days)
    await session.commit()
    await session.refresh(user)
    return user
