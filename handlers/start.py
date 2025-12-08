# handlers/start.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from keyboards import get_main_menu_kb
from config import settings

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привіт! \nЦе бот зворотного зв’язку для новинного каналу.\nОбери, що хочеш надіслати:",
        reply_markup=get_main_menu_kb()
    )

@router.message(Command("id"))
async def cmd_id(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    await message.answer(f"Твій ID: <code>{message.from_user.id}</code>")

@router.message(F.text.lower().in_(["меню", "головне меню", "назад"]))
async def back_to_menu(message: Message):
    await message.answer("Головне меню:", reply_markup=get_main_menu_kb())

# Команда для перевірки групи (тільки адміни)
@router.message(Command("testgroup"))
async def test_group(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("Тільки для адмінів!")
        return
    try:
        await message.bot.send_message(
            settings.FEEDBACK_CHAT_ID,
            "Тестове повідомлення від бота \nЯкщо бачиш це — ID правильний!"
        )
        await message.answer("Повідомлення успішно надіслано в групу логів!")
    except Exception as e:
        await message.answer(f"Помилка: {e}\nПеревір FEEDBACK_CHAT_ID")
