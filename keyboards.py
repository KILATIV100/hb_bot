# keyboards.py — ФІНАЛЬНА РОБОЧА ВЕРСІЯ 2025
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📰 Надіслати новину"), KeyboardButton(text="📢 Запит про рекламу")],
            [KeyboardButton(text="💬 Інше повідомлення")],
            [KeyboardButton(text="ℹ️ Про бот"), KeyboardButton(text="❓ Допомога")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return kb


def get_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Відправити", callback_data="confirm_send"),
            InlineKeyboardButton(text="Скасувати", callback_data="cancel_send")
        ]
    ])
    return kb


def get_anonymity_kb() -> InlineKeyboardMarkup:
    """Клавіатура для вибору способу відправки"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Підписано", callback_data="anonymous_no"),
            InlineKeyboardButton(text="👻 Анонімно", callback_data="anonymous_yes")
        ],
        [
            InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_send")
        ]
    ])
    return kb


def get_edit_kb() -> InlineKeyboardMarkup:
    """Клавіатура для редагування перед відправкою"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_message"),
            InlineKeyboardButton(text="✅ Відправити", callback_data="confirm_send")
        ],
        [
            InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_send")
        ]
    ])
    return kb
