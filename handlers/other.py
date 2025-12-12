# handlers/other.py
from typing import List
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.feedback_states import FeedbackStates
from utils.notify_admins import notify_admins
from keyboards import get_confirm_kb, get_main_menu_kb
from database.db import db

router = Router()

@router.message(F.text.in_(["💬 Зворотний зв'язок", "💬 Інше повідомлення", "Інше повідомлення"]))
async def start_other(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("🚫 Будь ласка, зачекай 10 секунд.")
        return
    await state.set_state(FeedbackStates.waiting_for_other)
    await state.update_data(feedback_type="other")
    await message.answer("💬 Напишіть нам:\n\nПитання, пропозиція чи просто відгук. Слухаємо вас!")

@router.message(FeedbackStates.waiting_for_other)
async def receive_other(message: Message, state: FSMContext, album: List[Message] = None):
    content = "Без тексту"
    media_files = [] 
    if album:
        for msg in album:
            if msg.caption: content = msg.caption; break
            if msg.text: content = msg.text; break
        for msg in album:
            if msg.photo: media_files.append({'file_id': msg.photo[-1].file_id, 'type': 'photo'})
            elif msg.video: media_files.append({'file_id': msg.video.file_id, 'type': 'video'})
            elif msg.document: media_files.append({'file_id': msg.document.file_id, 'type': 'document'})
    else:
        content = message.text or message.caption or "Без тексту"
        if message.photo: media_files.append({'file_id': message.photo[-1].file_id, 'type': 'photo'})
        elif message.video: media_files.append({'file_id': message.video.file_id, 'type': 'video'})
        elif message.document: media_files.append({'file_id': message.document.file_id, 'type': 'document'})

    await state.update_data(content=content, media_files=media_files)
    
    msg_preview = f"🔍 Перевірка:\n\n📝 <b>Текст:</b> {content[:200]}"
    if media_files: msg_preview += f"\n📎 <b>Файлів:</b> {len(media_files)} шт."
    msg_preview += "\n\n<i>Відправляємо?</i>"

    await message.answer(msg_preview, reply_markup=get_confirm_kb())
    await state.set_state(FeedbackStates.confirming)

@router.callback_query(F.data == "confirm_send", FeedbackStates.confirming)
async def confirm_other(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    username = callback.from_user.username or "Без імені"
    content = data.get("content", "")
    media_files = data.get("media_files", [])

    feedback_id = await db.add_feedback(callback.from_user.id, username, "інше", content)
    for m in media_files: await db.add_media(feedback_id, m['file_id'], m['type'])

    await notify_admins(
        bot=bot,
        user_id=callback.from_user.id,
        username=username,
        category="інше",
        feedback_id=feedback_id,
        text=content,
        media_files=media_files,
        is_anonymous=False
    )

    await callback.message.answer("✅ Повідомлення отримано! Дякуємо ❤️", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_send")
async def cancel_other(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Скасовано.", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()
    # handlers/other.py (Додайте це в кінець файлу)
from aiogram.types import ChatMemberUpdated
from config import settings

@router.my_chat_member()
async def on_bot_added_to_channel_or_group(event: ChatMemberUpdated, bot: Bot):
    """
    Автоматично виходить з невідомих груп та каналів.
    Дозволяє бути тільки в основному каналі (CHANNEL_ID).
    """
    # Ігноруємо оновлення в особистих чатах
    if event.chat.type == "private":
        return

    # Якщо бота додали в "наш" канал — все ок, залишаємось
    if event.chat.id == settings.CHANNEL_ID:
        return

    # У всіх інших випадках (ліві групи, канали) — виходимо
    try:
        # Можна спробувати написати прощальне повідомлення (якщо є права)
        await bot.send_message(event.chat.id, "🚫 Цей бот працює тільки в режимі прийому новин в особистих повідомленнях.")
    except:
        pass
    
    # Виходимо з чату
    await bot.leave_chat(event.chat.id)
