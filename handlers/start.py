# handlers/start.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from keyboards import get_main_menu_kb
from config import settings

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 Привіт!\n\n"
        "Це офіційний бот зворотного зв'язку для новинного каналу 📰\n\n"
        "З його допомогою ти можеш:\n"
        "• 📰 Надіслати цікаву новину\n"
        "• 📢 Запропонувати рекламне спілкування\n"
        "• 💬 Задати питання або поділитися ідеєю\n\n"
        "Що дальше?"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_kb())

@router.message(Command("id"))
async def cmd_id(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    await message.answer(f"Твій ID: <code>{message.from_user.id}</code>")

@router.message(F.text.lower().in_(["меню", "головне меню", "назад"]))
async def back_to_menu(message: Message):
    await message.answer("📋 Головне меню:", reply_markup=get_main_menu_kb())

@router.message(F.text.startswith("📰"))
async def handle_news_button(message: Message):
    # Обробляється через handlers/news.py
    pass

@router.message(F.text.startswith("📢"))
async def handle_ad_button(message: Message):
    # Обробляється через handlers/ad.py
    pass

@router.message(F.text.startswith("💬"))
async def handle_other_button(message: Message):
    # Обробляється через handlers/other.py
    pass

@router.message(F.text == "ℹ️ Про бот")
async def cmd_about(message: Message):
    about_text = (
        "ℹ️ <b>Про бот</b>\n\n"
        "Це модерний бот зворотного зв'язку, розроблений для збору:\n"
        "✓ Новин від спільноти\n"
        "✓ Рекламних пропозицій\n"
        "✓ Пропозицій та критики\n\n"
        "<b>Версія:</b> 2.1 (New features)\n"
        "<b>Мова:</b> Python + aiogram\n"
        "<b>БД:</b> PostgreSQL\n\n"
        "Усі повідомлення закономірно логуються для аналізу."
    )
    await message.answer(about_text, reply_markup=get_main_menu_kb())

@router.message(F.text == "❓ Допомога")
async def cmd_help(message: Message):
    help_text = (
        "❓ <b>Як користуватись ботом?</b>\n\n"
        "<b>📰 Надіслати новину:</b>\n"
        "Натисни кнопку, напиши текст або прикріпи фото/відео\n"
        "Перевір передпереглядом і відправ\n\n"
        "<b>📢 Запит про рекламу:</b>\n"
        "Напиши про твою пропозицію - ми зв'яжемося!\n\n"
        "<b>💬 Інше повідомлення:</b>\n"
        "Питання, пропозиції, критика - поділись з нами!\n\n"
        "<b>⏱️ Обмеження:</b>\n"
        "Одне повідомлення на 5 хвилин\n\n"
        "<b>❓ Питання?</b>\n"
        "Напиши /help для довідки"
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb())

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
