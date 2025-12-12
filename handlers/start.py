# handlers/start.py
from typing import List
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart, Command, StateFilter
from keyboards import get_main_menu_kb, get_start_kb
from config import settings
from database.db import db
from utils.notify_admins import notify_admins

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 Привіт! Дімон на звʼязку!\n\n"
        "Це офіційний бот XBrovary 📰\n"
        "Тут ти можеш поділитися новиною, замовити рекламу або просто написати нам.\n\n"
        "Натисни кнопку нижче, щоб почати!"
    )
    await message.answer(welcome_text, reply_markup=get_start_kb())

@router.message(F.text.in_(["▶️ СТАРТ", "▶️ РОЗПОЧАТИ"]))
async def cmd_menu(message: Message):
    menu_text = (
        "📋 ГОЛОВНЕ МЕНЮ\n\n"
        "Будь ласка, оберіть дію:"
    )
    await message.answer(menu_text, reply_markup=get_main_menu_kb())

@router.message(Command("id"))
async def cmd_id(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    await message.answer(f"Твій ID: <code>{message.from_user.id}</code>")

@router.message(F.text.lower().in_(["меню", "головне меню", "назад"]))
async def back_to_menu(message: Message):
    await message.answer("📋 Повертаємось у головне меню:", reply_markup=get_main_menu_kb())

@router.message(F.text == "ℹ️ Про бота")
async def cmd_about(message: Message):
    about_text = (
        "ℹ️ Про бота\n\n"
        "Цей бот створено для зручного зв'язку з редакцією XBrovary.\n\n"
        "Ми приймаємо:\n"
        "✅ Новини від підписників\n"
        "✅ Запити на рекламу\n"
        "✅ Пропозиції та зауваження\n\n"
        "Всі повідомлення читають живі люди (адміни)."
    )
    await message.answer(about_text, reply_markup=get_main_menu_kb())

@router.message(F.text == "❓ Допомога")
async def cmd_help_button(message: Message):
    help_text = (
        "❓ Як користуватись ботом?\n\n"
        "<b>📰 Надіслати новину:</b>\n"
        "Натисни кнопку, напиши текст та прикріпи фото/відео.\n\n"
        "<b>📢 Реклама:</b>\n"
        "Маєш бізнес? Напиши нам пропозицію.\n\n"
        "<b>⚡️ Швидка відправка:</b>\n"
        "Ти можеш просто написати в цей чат або надіслати фото — бот передасть це адмінам.\n\n"
        "⚠️ <i>Обмеження: 1 повідомлення на 10 секунд.</i>"
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb())

@router.message(Command("help"))
async def cmd_help(message: Message):
    is_admin = message.from_user.id in settings.ADMIN_IDS
    
    help_text = (
        "❓ Довідка\n\n"
        "• Використовуйте меню для навігації.\n"
        "• Ви можете надсилати текст, фото, відео та альбоми.\n"
        "• Антиспам: 10 секунд між повідомленнями.\n"
    )

    if is_admin:
        help_text += (
            "\n👮‍♂️ АДМІН-ПАНЕЛЬ\n"
            "-----------------------------\n"
            "<b>📸 Водяні знаки:</b>\n"
            "• Автоматично накладаються на ФОТО та ВІДЕО.\n"
            "• Підтримка альбомів.\n\n"
            "<b>📊 Команди:</b>\n"
            "• /stats - статистика\n"
            "• /news, /ads, /other - фільтри\n"
            "• Відповідь користувачу: кнопкою або свайпом."
        )
    
    await message.answer(help_text, reply_markup=get_main_menu_kb())

@router.message(
    StateFilter(None),
    (F.text & ~F.text.in_(["📰 Надіслати новину", "📢 Запит про рекламу", "💬 Інше повідомлення",
                           "ℹ️ Про бот", "❓ Допомога", "меню", "головне меню", "назад", "▶️ СТАРТ"]))
    | F.photo | F.video | F.document
)
async def handle_direct_message(message: Message, bot: Bot, album: List[Message] = None):
    # Антиспам 10 секунд
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("⏳ Не так швидко! Зачекай 10 секунд.")
        return

    username = message.from_user.username or "Без імені"
    content = "Без тексту"
    media_files = []

    # Обробка альбому (якщо надіслано декілька файлів)
    if album:
        for msg in album:
            if msg.caption: content = msg.caption; break
            if msg.text: content = msg.text; break
        for msg in album:
            if msg.photo: media_files.append({'file_id': msg.photo[-1].file_id, 'type': 'photo'})
            elif msg.video: media_files.append({'file_id': msg.video.file_id, 'type': 'video'})
            elif msg.document: media_files.append({'file_id': msg.document.file_id, 'type': 'document'})
    else:
        # Обробка одиночного повідомлення
        content = message.text or message.caption or "Без тексту"
        if message.photo: media_files.append({'file_id': message.photo[-1].file_id, 'type': 'photo'})
        elif message.video: media_files.append({'file_id': message.video.file_id, 'type': 'video'})
        elif message.document: media_files.append({'file_id': message.document.file_id, 'type': 'document'})

    # 🔥 ЧАТ-ФІЧА: Перевіряємо, чи це відповідь на повідомлення бота (Reply)
    # Це дозволяє користувачу відповідати на повідомлення адміна свайпом
    if message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or "[Медіа]"
        if len(replied_text) > 50: replied_text = replied_text[:50] + "..."
        
        reply_context = f"\n\n↩️ <b>Користувач відповів на:</b> <i>«{replied_text}»</i>"
        content = f"{content}{reply_context}"

    # 1. Створюємо запис в БД (текст)
    feedback_id = await db.add_feedback(
        user_id=message.from_user.id, 
        username=username, 
        category="інше", 
        content=content
    )

    # 2. Додаємо медіа файли в базу
    for m in media_files:
        await db.add_media(feedback_id, m['file_id'], m['type'])

    # 3. Відправляємо адмінам
    await notify_admins(
        bot=bot,
        user_id=message.from_user.id,
        username=username,
        category="інше",
        feedback_id=feedback_id,
        text=content,
        media_files=media_files,
        is_anonymous=False
    )

    await message.answer("✅ Повідомлення надіслано!", reply_markup=get_main_menu_kb())
