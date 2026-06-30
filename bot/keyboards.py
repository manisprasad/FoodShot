from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from core.i18n import I18n

def weight_adjust_keyboard(current_weight: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="-50g", callback_data="weight:-50"),
        InlineKeyboardButton(text="-10g", callback_data="weight:-10"),
        InlineKeyboardButton(text="+10g", callback_data="weight:10"),
        InlineKeyboardButton(text="+50g", callback_data="weight:50")
    )
    return builder.as_markup()

def main_menu(i18n: I18n) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    history_text = "📜 Історія" if i18n.lang == "uk" else "📜 History"
    settings_text = "⚙️ Налаштування" if i18n.lang == "uk" else "⚙️ Settings"
    
    builder.row(
        KeyboardButton(text=history_text),
        KeyboardButton(text=settings_text)
    )
    return builder.as_markup(resize_keyboard=True)

def language_menu(current_lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇬🇧 English" + (" ✅" if current_lang == "en" else ""), callback_data="set_lang:en"),
        InlineKeyboardButton(text="🇺🇦 Українська" + (" ✅" if current_lang == "uk" else ""), callback_data="set_lang:uk")
    )
    return builder.as_markup()
