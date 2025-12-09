# handlers/start.py
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_kb
from config import settings
from database.db import db
from utils.notify_admins import notify_admins

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 Привіт!\n\n"
        "Це офіційний бот XBrovary зворотного зв'язку 📰\n\n"
        "З його допомогою ти можеш:\n"
        "• 📰 Надіслати цікаву новину\n"
        "• 📢 Запропонувати рекламне спілкування\n"
        "• 💬 Задати питання або поділитися ідеєю\n\n"
        "Що далі?"
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

@router.message(F.text == "ℹ️ Про бот")
async def cmd_about(message: Message):
    about_text = (
        "ℹ️ <b>Про бот</b>\n\n"
        "Це модерний бот зворотного зв'язку, розроблений Адміном каналу для збору:\n"
        "✓ Новин від спільноти\n"
        "✓ Рекламних пропозицій\n"
        "✓ Пропозицій та критики\n\n"
        "Бот закономірно логує всі повідомлення для аналізу та якісного контролю."
    )
    await message.answer(about_text, reply_markup=get_main_menu_kb())

@router.message(F.text == "❓ Допомога")
async def cmd_help_button(message: Message):
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
        "Одне повідомлення на 1 хвилину (Антиспам)\n\n"
        "<b>❓ Питання?</b>\n"
        "Напиши /help для довідки"
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb())

@router.message(Command("help"))
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
        "Одне повідомлення на 1 хвилину (Антиспам)\n\n"
        "<b>Команди адмінів:</b>\n"
        "/stats - аналітика\n"
        "/id - твій ID\n"
        "/testgroup - тест групи логів"
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

# Обробник для прямих текстових повідомлень (без меню)
@router.message(F.text)
async def handle_direct_message(message: Message, bot: Bot):
    """Ловить звичайні текстові повідомлення, написані прямо в боті"""
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 1 хвилину перед наступною відправкою 🚫")
        return

    username = message.from_user.username or "Без імені"

    # Додаємо feedback як "інше"
    feedback_id = await db.add_feedback(message.from_user.id, username, "інше", message.text)

    # Відправляємо в групу логів
    group_message_id = await notify_admins(
        bot=bot,
        user_id=message.from_user.id,
        username=username,
        category="інше",
        feedback_id=feedback_id,
        text=message.text,
        is_anonymous=False
    )

    # Зберігаємо group_message_id
    if group_message_id:
        await db.update_group_message_id(feedback_id, group_message_id)

    await message.answer("✅ Твоє повідомлення отримано! Дякуємо за участь ❤️", reply_markup=get_main_menu_kb())
