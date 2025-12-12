# handlers/start.py
from typing import List
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_kb, get_start_kb
from config import settings
from database.db import db
from utils.notify_admins import notify_admins

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 Привіт Дімон на звʼязку!\n\n"
        "Це офіційний бот XBrovary 📰\n\n"
        "Натисни СТАРТ щоб почати!"
    )
    await message.answer(welcome_text, reply_markup=get_start_kb())

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
        "Натисни кнопку, напиши текст або прикріпи фото/відео.\n\n"
        "<b>📢 Реклама та Інше:</b>\n"
        "Обери відповідну кнопку в меню.\n\n"
        "<b>⚡️ Швидка відправка:</b>\n"
        "Просто надішли боту повідомлення, фото або відео, і воно потрапить адмінам!\n\n"
        "<b>⏱️ Обмеження:</b>\n"
        "Одне повідомлення на 1 хвилину."
    )
    await message.answer(help_text, reply_markup=get_main_menu_kb())

@router.message(Command("help"))
async def cmd_help(message: Message):
    is_admin = message.from_user.id in settings.ADMIN_IDS
    
    help_text = (
        "❓ <b>Довідка</b>\n\n"
        "<b>Користувачам:</b>\n"
        "• Використовуйте кнопки меню для відправки новин/реклами.\n"
        "• Або просто пишіть повідомлення/кидайте медіа в чат.\n"
    )

    if is_admin:
        help_text += (
            "\n👮‍♂️ <b>ПАНЕЛЬ АДМІНІСТРАТОРА</b>\n"
            "-----------------------------\n"
            "<b>📸 Водяні знаки:</b>\n"
            "• Працює для ФОТО та ВІДЕО.\n"
            "• Логотип накладається у <b>5 точках</b> (центр + кути).\n"
            "• Підтримуються АЛЬБОМИ (до 10 файлів).\n\n"
            "<b>📊 Команди:</b>\n"
            "• /stats - статистика\n"
            "• /news, /ads, /other - фільтри\n"
            "• /id - показати ID"
        )
    
    await message.answer(help_text, reply_markup=get_main_menu_kb())

# Обробник для прямих повідомлень (текст ТА медіа)
@router.message(
    StateFilter(None),
    (F.text & ~F.text.in_(["📰 Надіслати новину", "📢 Запит про рекламу", "💬 Інше повідомлення",
                           "ℹ️ Про бот", "❓ Допомога", "меню", "головне меню", "назад", "▶️ СТАРТ"]))
    | F.photo | F.video | F.document
)
async def handle_direct_message(message: Message, bot: Bot, album: List[Message] = None):
    """Ловить звичайні повідомлення (текст + медіа), написані прямо в боті"""
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 1 хвилину перед наступною відправкою 🚫")
        return

    username = message.from_user.username or "Без імені"
    content = "Без тексту"
    media_files = [] # Список словників [{'file_id': '...', 'type': 'photo'}]

    # 1. Логіка збору медіа (підтримка альбомів)
    if album:
        # Шукаємо текст
        for msg in album:
            if msg.caption: content = msg.caption; break
            if msg.text: content = msg.text; break
        
        # Збираємо файли
        for msg in album:
            if msg.photo:
                media_files.append({'file_id': msg.photo[-1].file_id, 'type': 'photo'})
            elif msg.video:
                media_files.append({'file_id': msg.video.file_id, 'type': 'video'})
            elif msg.document:
                media_files.append({'file_id': msg.document.file_id, 'type': 'document'})
    else:
        # Одиночне повідомлення
        content = message.text or message.caption or "Без тексту"
        if message.photo:
            media_files.append({'file_id': message.photo[-1].file_id, 'type': 'photo'})
        elif message.video:
            media_files.append({'file_id': message.video.file_id, 'type': 'video'})
        elif message.document:
            media_files.append({'file_id': message.document.file_id, 'type': 'document'})

    # 2. Створюємо запис в БД (ТІЛЬКИ ТЕКСТ, без file_id)
    # Функція add_feedback тепер не приймає фото/відео аргументів
    feedback_id = await db.add_feedback(
        user_id=message.from_user.id, 
        username=username, 
        category="інше", 
        content=content
    )

    # 3. Додаємо медіа в нову таблицю
    for m in media_files:
        await db.add_media(feedback_id, m['file_id'], m['type'])

    # 4. Відправляємо адмінам (використовуємо нову логіку зі списком media_files)
    await notify_admins(
        bot=bot,
        user_id=message.from_user.id,
        username=username,
        category="інше",
        feedback_id=feedback_id,
        text=content,
        media_files=media_files, # <-- Передаємо список
        is_anonymous=False
    )

    await message.answer("✅ Твоє повідомлення отримано! Дякуємо за участь ❤️", reply_markup=get_main_menu_kb())
