# handlers/start.py
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from keyboards import get_main_menu_kb, get_start_kb
from config import settings
from database.db import db
from utils.notify_admins import notify_admins
import logging

# Налаштовуємо логер для цього файлу
logger = logging.getLogger(__name__)

router = Router()

# Використовуємо Command("start") як надійніший варіант, + CommandStart() про всяк випадок
@router.message(Command("start"))
@router.message(CommandStart())
async def cmd_start(message: Message):
    logger.info(f"🟢 Отримано команду /start від {message.from_user.id}")
    
    welcome_text = (
        "👋 Привіт, Дімон на звʼязку!\n\n"
        "Це офіційний бот XBrovary 📰\n\n"
        "Натисни СТАРТ щоб почати!"
    )
    try:
        await message.answer(welcome_text, reply_markup=get_start_kb())
        logger.info("✅ Вітальне повідомлення надіслано")
    except Exception as e:
        logger.error(f"❌ Помилка при надсиланні вітання: {e}")

@router.message(F.text == "▶️ СТАРТ")
async def cmd_menu(message: Message):
    menu_text = (
        "📋 <b>ГОЛОВНЕ МЕНЮ</b>\n\n"
        "Обери дію:"
    )
    await message.answer(menu_text, reply_markup=get_main_menu_kb())

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
        "Це бот зворотного зв'язку для збору:\n"
        "✓ Новин від спільноти\n"
        "✓ Рекламних пропозицій\n"
        "✓ Пропозицій та критики\n\n"
        "Всі повідомлення логуються для аналізу та якісного контролю.\n"
        "Розроблений @kilativ100"
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
        "/news - новини\n"
        "/ads - реклама\n"
        "/other - інше"
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb())

# Обробник для прямих текстових повідомлень (без меню)
@router.message(F.text,
               ~F.text.in_(["📰 Надіслати новину", "📢 Запит про рекламу", "💬 Інше повідомлення",
                           "ℹ️ Про бот", "❓ Допомога", "меню", "головне меню", "назад", "▶️ СТАРТ"]))
async def handle_direct_message(message: Message, bot: Bot):
    """Ловить звичайні текстові повідомлення, написані прямо в боті"""
    
    # ⚠️ ВАЖЛИВО: Перевіряємо, чи DB має пул з'єднань (нова версія)
    if hasattr(db, 'pool') and db.pool is None:
         logger.error("❌ DB Pool is closed or not initialized!")
         await message.answer("🔧 Технічна перерва (Database Error)")
         return

    try:
        username = message.from_user.username or "Без імені"

        # Додаємо feedback як "інше"
        feedback_id = await db.add_feedback(message.from_user.id, username, "інше", message.text)

        # Відправляємо адмінам
        await notify_admins(
            bot=bot,
            user_id=message.from_user.id,
            username=username,
            category="інше",
            feedback_id=feedback_id,
            text=message.text,
            is_anonymous=False
        )

        await message.answer("✅ Твоє повідомлення отримано! Дякуємо за участь ❤️", reply_markup=get_main_menu_kb())
    except Exception as e:
        logger.error(f"❌ Помилка в handle_direct_message: {e}")
        await message.answer("Щось пішло не так 😔")
