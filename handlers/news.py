# handlers/news.py
from typing import List
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.feedback_states import FeedbackStates
from utils.notify_admins import notify_admins
from keyboards import get_confirm_kb, get_main_menu_kb
from database.db import db

router = Router()

@router.message(F.text.in_(["📰 Надіслати новину", "Надіслати новину"]))
async def start_news(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 1 хвилину перед наступною відправкою 🚫")
        return
    await state.set_state(FeedbackStates.waiting_for_news)
    await state.update_data(feedback_type="news")
    await message.answer("📰 Надішли новину (можна декілька фото/відео одразу):")

@router.message(FeedbackStates.waiting_for_news)
async def receive_news(message: Message, state: FSMContext, album: List[Message] = None):
    content = "Без тексту"
    media_files = [] # Список словників [{'file_id': '...', 'type': 'photo'}]

    if album:
        # Збираємо текст з будь-якого файлу в альбомі
        for msg in album:
            if msg.caption: content = msg.caption; break
            if msg.text: content = msg.text; break
        
        # Збираємо ВСІ файли
        for msg in album:
            if msg.photo:
                media_files.append({'file_id': msg.photo[-1].file_id, 'type': 'photo'})
            elif msg.video:
                media_files.append({'file_id': msg.video.file_id, 'type': 'video'})
            elif msg.document:
                media_files.append({'file_id': msg.document.file_id, 'type': 'document'})
    else:
        # Звичайне повідомлення (один файл)
        content = message.text or message.caption or "Без тексту"
        if message.photo:
            media_files.append({'file_id': message.photo[-1].file_id, 'type': 'photo'})
        elif message.video:
            media_files.append({'file_id': message.video.file_id, 'type': 'video'})
        elif message.document:
            media_files.append({'file_id': message.document.file_id, 'type': 'document'})

    await state.update_data(content=content, media_files=media_files)

    # Прев'ю
    msg_preview = f"Перевірно?\n\n📝 <b>Текст:</b> {content[:200]}"
    if media_files:
        msg_preview += f"\n📎 <b>Файлів:</b> {len(media_files)} шт."

    await message.answer(msg_preview, reply_markup=get_confirm_kb())
    await state.set_state(FeedbackStates.confirming)

@router.callback_query(F.data == "confirm_send", FeedbackStates.confirming)
async def confirm_news(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    username = callback.from_user.username or "Без імені"
    content = data.get("content", "")
    media_files = data.get("media_files", [])

    # 1. Створюємо запис новини
    feedback_id = await db.add_feedback(callback.from_user.id, username, "новина", content)

    # 2. Зберігаємо всі медіа в базу
    for m in media_files:
        await db.add_media(feedback_id, m['file_id'], m['type'])

    # 3. Сповіщаємо адмінів (надсилаємо перший файл як приклад)
    first_file_id = media_files[0]['file_id'] if media_files else None
    
    # Визначаємо тип першого файлу для сповіщення
    photo_obj = None
    video_obj = None
    doc_obj = None
    
    if media_files:
        if media_files[0]['type'] == 'photo': photo_obj = first_file_id
        elif media_files[0]['type'] == 'video': video_obj = first_file_id
        elif media_files[0]['type'] == 'document': doc_obj = first_file_id

    # Додаємо примітку, якщо це альбом
    admin_text = content
    if len(media_files) > 1:
        admin_text = f"[АЛЬБОМ: {len(media_files)} файлів]\n" + admin_text

    await notify_admins(
        bot=bot,
        user_id=callback.from_user.id,
        username=username,
        category="новина",
        feedback_id=feedback_id,
        text=admin_text,
        photo=photo_obj,
        video=video_obj,
        document=doc_obj
    )

    await callback.message.answer("Дякуємо! Новина надіслана ❤️", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_send")
async def cancel_news(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Скасовано. Обери дію:", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()
