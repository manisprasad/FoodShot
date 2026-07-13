from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MealLog, User


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, **kwargs) -> User:
    user = User(**kwargs)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user_id: int, **kwargs) -> User | None:
    user = await get_user(session, user_id)
    if user:
        for key, value in kwargs.items():
            setattr(user, key, value)
        await session.flush()
        await session.refresh(user)
    return user


async def create_meal_log(session: AsyncSession, **kwargs) -> MealLog:
    meal = MealLog(**kwargs)
    session.add(meal)
    await session.flush()
    await session.refresh(meal)
    return meal


async def get_user_history(
    session: AsyncSession, user_id: int, limit: int = 10
) -> list[MealLog]:
    result = await session.execute(
        select(MealLog)
        .where(MealLog.user_id == user_id)
        .order_by(MealLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_user_language(session: AsyncSession, user_id: int, language: str):
    await session.execute(
        update(User).where(User.id == user_id).values(language=language)
    )
    await session.flush()


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    user = await get_user(session, user_id)
    if user:
        await session.delete(user)
        await session.flush()
        return True
    return False


async def get_meal_logs_in_range(
    session: AsyncSession, user_id: int, start_date: datetime, end_date: datetime
) -> list[MealLog]:
    result = await session.execute(
        select(MealLog)
        .where(
            MealLog.user_id == user_id,
            MealLog.created_at >= start_date,
            MealLog.created_at <= end_date,
        )
        .order_by(MealLog.created_at.asc())
    )
    return list(result.scalars().all())


async def delete_old_meal_logs(session: AsyncSession, before_date: datetime) -> int:
    result = await session.execute(
        delete(MealLog).where(MealLog.created_at < before_date)
    )
    await session.flush()
    return result.rowcount


async def get_users_with_logs_on_day(
    session: AsyncSession, start_time: datetime, end_time: datetime
) -> list[int]:
    result = await session.execute(
        select(MealLog.user_id)
        .where(MealLog.created_at >= start_time, MealLog.created_at <= end_time)
        .distinct()
    )
    return list(result.scalars().all())


async def get_active_months(
    session: AsyncSession, user_id: int
) -> list[tuple[int, int]]:
    result = await session.execute(
        select(MealLog.created_at)
        .where(MealLog.user_id == user_id)
        .order_by(MealLog.created_at.desc())
    )
    dates = result.scalars().all()
    seen = set()
    active = []
    for dt in dates:
        key = (dt.year, dt.month)
        if key not in seen:
            seen.add(key)
            active.append(key)
    return active


async def delete_meal_log(session: AsyncSession, meal_id: int) -> bool:
    result = await session.execute(select(MealLog).where(MealLog.id == meal_id))
    meal = result.scalar_one_or_none()
    if meal:
        await session.delete(meal)
        await session.flush()
        return True
    return False


async def get_users_for_daily_report(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(
            User.daily_report_enabled.is_(True),
            User.daily_calorie_target.is_not(None),
        )
    )
    return list(result.scalars().all())
