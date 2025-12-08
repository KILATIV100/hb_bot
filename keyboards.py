# keyboards.py — фінальна версія (з емодзі)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.row("Надіслати новину")
    kb.row("Запит про рекламу")
    kb.row("Інше повідомлення")
    return kb


def get_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Відправити", callback_data="confirm_send"),
        InlineKeyboardButton("Скасувати", callback_data="cancel_send")
    )
    return kb
