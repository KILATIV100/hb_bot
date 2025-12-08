# keyboards.py (без змін)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)  # one_time=False, щоб меню лишалося
    kb.add(KeyboardButton("Надіслати новину 📢"))
    kb.add(KeyboardButton("Запит про рекламу 💼"))
    kb.add(KeyboardButton("Інше повідомлення ✉️"))
    return kb

def get_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Відправити ✅", callback_data="confirm_send"))
    kb.add(InlineKeyboardButton("Скасувати ❌", callback_data="cancel_send"))
    return kb
