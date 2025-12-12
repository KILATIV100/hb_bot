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

@router.message(F.text.in_(["💬 Інше повідомлення", "Інше повідомлення"]))
async def start_other(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 1 хвилину перед наступною відправкою 🚫")
        return
    await state.set_state(FeedbackStates.waiting_for_other)
    await state.update_data(feedback_type="other")
    await message.answer("💬 Надішли своє повідомлення (текст + фото/відео/файл):")

# 👇 ОНОВЛЕНИЙ ОБРОБНИК (З підтримкою альбомів)
@router.message(FeedbackStates.waiting_for_other)
async def receive_other(message: Message, state: FSMContext, album: List[Message] = None):
    """
    Обробляє повідомлення або альбом для 'іншого'.
    """
    content = "Без тексту"
    media_obj = None

    # 1. Логіка для АЛЬБОМУ
    if album:
        for msg in album:
            if msg.caption:
                content = msg.caption
                break
            if msg.text:
                content = msg.text
                break
        
        first_msg = album[0]
        if first_msg.photo:
            media_obj = first_msg.photo
        elif first_msg.video:
            media_obj = first_msg.video
        elif first_msg.document:
            media_obj = first_msg.document
            
    # 2. Логіка для ЗВИЧАЙНОГО повідомлення
    else:
        content = message.text or message.caption or "Без тексту"
        media_obj = message.photo or message.video or message.document

    # Зберігаємо
    await state.update_data(
        content=content,
        media=media_obj
    )

    # Попередній перегляд
    preview_text = content
    if len(preview_text) > 200:
        preview_text = preview_text[:200] + "..."
    
    msg_preview = f"Перевірно?\n\n📝 <b>Текст:</b> {preview_text}"
    if media_obj:
        msg_preview += "\n📎 <b>Медіа:</b> Прикріплено (1 файл)"
        if album and len(album) > 1:
             msg_preview += f"\n⚠️ <i>З альбому буде надіслано тільки перший файл</i>"

    await message.answer(msg_preview, reply_markup=get_confirm_kb())
    await state.set_state(FeedbackStates.confirming)

@router.callback_query(F.data == "confirm_send", FeedbackStates.confirming)
async def confirm_other(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    username = callback.from_user.username or "Без імені"

    media = data.get("media")
    photo_file_id = None
    video_file_id = None
    document_file_id = None

    if isinstance(media, list):  # Це фото (list[PhotoSize])
        photo_file_id = media[-1].file_id
    elif hasattr(media, 'file_id'):
        if hasattr(media, 'duration'):  # Це відео
            video_file_id = media.file_id
        else:  # Це документ
            document_file_id = media.file_id

    feedback_id = await db.add_feedback(callback.from_user.id, username, "інше", data["content"],
                                       photo_file_id=photo_file_id, video_file_id=video_file_id,
                                       document_file_id=document_file_id)

    await notify_admins(
        bot=bot,
        user_id=callback.from_user.id,
        username=username,
        category="інше",
        feedback_id=feedback_id,
        text=data["content"],
        photo=data.get("media") if isinstance(data.get("media"), list) else None,
        document=data.get("media") if hasattr(data.get("media", {}), 'file_id') and not isinstance(data.get("media"), list) else None,
        video=data.get("media") if hasattr(data.get("media", {}), 'file_id') else None,
        is_anonymous=False
    )

    await callback.message.answer("Дякуємо! Повідомлення надіслано ❤️", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_send")
async def cancel_other(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Скасовано. Обери дію:", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()
