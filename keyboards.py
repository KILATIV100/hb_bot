# keyboards.py — ФІНАЛЬНА РОБОЧА ВЕРСІЯ 2025
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Надіслати новину")],
            [KeyboardButton(text="Запит про рекламу")],
            [KeyboardButton(text="Інше повідомлення")]
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
