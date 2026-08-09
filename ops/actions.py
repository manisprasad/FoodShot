from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiogram import Bot
from sqlalchemy import func, select

from core import time_utils
from core.config import config
from core.i18n import I18n
from db.database import SessionLocal
from db.models import MealLog, User
from services import freemium


@dataclass
class UserOpRow:
    id: int
    username: str
    language: str
    diabetes_mode: bool
    is_premium: bool
    premium_until: datetime | None
    total_meals: int
    created_at: datetime | None


async def fetch_ops_users() -> list[UserOpRow]:
    """Fetch all users from DB with aggregated meal counts for the TUI data table."""
    async with SessionLocal() as session:
        stmt = (
            select(
                User,
                func.count(MealLog.id).label("total_meals"),
            )
            .outerjoin(MealLog, User.id == MealLog.user_id)
            .group_by(User.id)
            .order_by(User.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = []
        now = time_utils.get_utc_now()
        for user, count in result.all():
            rows.append(
                UserOpRow(
                    id=user.id,
                    username=user.username or "—",
                    language=user.language or "en",
                    diabetes_mode=bool(user.diabetes_mode),
                    is_premium=freemium.is_user_premium(user, now),
                    premium_until=user.premium_until,
                    total_meals=count,
                    created_at=user.created_at,
                )
            )
        return rows


async def op_grant_premium(user_id: int, days: float = 0, minutes: int = 0) -> bool:
    """Grant premium status and notify user via Telegram Bot API if configured."""
    async with SessionLocal() as session:
        user = await freemium.grant_user_premium(
            session, user_id=user_id, days=days, minutes=minutes
        )
        if not user:
            return False

    if config.BOT_TOKEN:
        try:
            bot = Bot(token=config.BOT_TOKEN)
            lang = user.language or "en"
            i18n = I18n(lang)

            if user.premium_until:
                local_until = time_utils.to_local_time(user.premium_until)
                until_date = local_until.strftime("%d.%m.%Y")
                until_time = local_until.strftime("%H:%M")
            else:
                until_date = "—"
                until_time = "—"

            if minutes > 0:
                days_bold = (
                    f"{minutes} хвилин" if lang == "uk" else f"{minutes} minutes"
                )
            else:
                days_bold = f"{int(days)} днів" if lang == "uk" else f"{int(days)} days"

            text = i18n.get(
                "premium-activated",
                days=days_bold,
                until_date=until_date,
                until_time=until_time,
            )
            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
            await bot.session.close()
        except Exception:
            pass
    return True


async def op_revoke_premium(user_id: int) -> bool:
    """Revoke premium status for user and send expired notification."""
    async with SessionLocal() as session:
        user = await freemium.revoke_user_premium(session, user_id=user_id)
        if not user:
            return False

    if config.BOT_TOKEN:
        try:
            bot = Bot(token=config.BOT_TOKEN)
            lang = user.language or "en"
            i18n = I18n(lang)

            text = i18n.get("premium-expired")
            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
            await bot.session.close()
        except Exception:
            pass
    return True


async def op_send_message(user_id: int, text: str) -> bool:
    """Send direct Telegram message to user from operations console."""
    if not config.BOT_TOKEN:
        return False

    try:
        bot = Bot(token=config.BOT_TOKEN)
        await bot.send_message(chat_id=user_id, text=text)
        await bot.session.close()
        return True
    except Exception:
        return False


async def fetch_user_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch recent meal logs for a specific user."""
    async with SessionLocal() as session:
        stmt = (
            select(MealLog)
            .where(MealLog.user_id == user_id)
            .order_by(MealLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        meals = result.scalars().all()
        rows = []
        for m in meals:
            local_dt = time_utils.to_local_time(m.created_at)
            rows.append(
                {
                    "id": m.id,
                    "dish_name": m.dish_name or "Unknown",
                    "portion_g": m.portion_g,
                    "carbs_g": m.carbs_g,
                    "kcal": m.kcal,
                    "bolus_dose": m.bolus_dose,
                    "created_at": local_dt.strftime("%Y-%m-%d %H:%M")
                    if local_dt
                    else "—",
                }
            )
        return rows
