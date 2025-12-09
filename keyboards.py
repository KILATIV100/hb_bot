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


def get_quick_replies_kb() -> InlineKeyboardMarkup:
    """Клавіатура з готовими відповідями для адмінів"""
    quick_replies = [
        ("✅ Опубліковано", "quick_reply_published"),
        ("⏳ На розгляді", "quick_reply_review"),
        ("❌ Відхилено", "quick_reply_rejected"),
        ("❓ Уточнити", "quick_reply_clarify"),
        ("💬 Власна відповідь", "quick_reply_custom"),
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=quick_replies[0][0], callback_data=quick_replies[0][1]),
         InlineKeyboardButton(text=quick_replies[1][0], callback_data=quick_replies[1][1])],
        [InlineKeyboardButton(text=quick_replies[2][0], callback_data=quick_replies[2][1]),
         InlineKeyboardButton(text=quick_replies[3][0], callback_data=quick_replies[3][1])],
        [InlineKeyboardButton(text=quick_replies[4][0], callback_data=quick_replies[4][1])],
    ])
    return kb
