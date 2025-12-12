# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_start_kb() -> ReplyKeyboardMarkup:
    """Клавіатура для першого запуску"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="▶️ РОЗПОЧАТИ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return kb

def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📰 Надіслати новину"), KeyboardButton(text="📢 Щодо реклами")],
            [KeyboardButton(text="💬 Зворотний зв'язок")], # Звучить краще, ніж "Інше"
            [KeyboardButton(text="ℹ️ Про нас"), KeyboardButton(text="❓ Допомога")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return kb

def get_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Відправити", callback_data="confirm_send"),
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
