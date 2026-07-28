from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiogram import Bot
from sqlalchemy import func, select

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
        for user, count in result.all():
            rows.append(
                UserOpRow(
                    id=user.id,
                    username=user.username or "—",
                    language=user.language or "en",
                    diabetes_mode=bool(user.diabetes_mode),
                    is_premium=bool(user.is_premium),
                    premium_until=user.premium_until,
                    total_meals=count,
                    created_at=user.created_at,
                )
            )
        return rows


async def op_grant_premium(user_id: int, days: int) -> bool:
    """Grant premium status and notify user via Telegram Bot API if configured."""
    async with SessionLocal() as session:
        user = await freemium.grant_user_premium(session, user_id=user_id, days=days)
        if not user:
            return False

    if config.BOT_TOKEN:
        try:
            bot = Bot(token=config.BOT_TOKEN)
            lang = user.language or "en"
            i18n = I18n(lang)

            until_date = (
                user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "—"
            )
            until_time = (
                user.premium_until.strftime("%H:%M") if user.premium_until else "—"
            )

            days_bold = f"{days} днів" if lang == "uk" else f"{days} days"

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
    """Revoke premium status for user."""
    async with SessionLocal() as session:
        user = await freemium.revoke_user_premium(session, user_id=user_id)
        return user is not None


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
        return [
            {
                "id": m.id,
                "dish_name": m.dish_name or "Unknown",
                "portion_g": m.portion_g,
                "carbs_g": m.carbs_g,
                "kcal": m.kcal,
                "bolus_dose": m.bolus_dose,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
                if m.created_at
                else "—",
            }
            for m in meals
        ]
