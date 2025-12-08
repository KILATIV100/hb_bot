# handlers/other.py (приклад; для ad/other — копіюй, міняй waiting_for_news/confirm на відповідне + category)
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from states.feedback_states import FeedbackStates
from aiogram.fsm.context import FSMContext
from utils.notify_admins import notify_admins
from keyboards import get_confirm_kb
from database.db import db

router = Router()

@router.message(FeedbackStates.waiting_for_other)
async def receive_news(message: Message, state: FSMContext):
    # Зберігаємо в state (текст + медіа)
    media = None
    if message.photo:
        media = message.photo
    elif message.document:
        media = message.document
    elif message.video:
        media = message.video
    await state.update_data(content=message.text or "Без тексту", media=media)
    preview = message.text or "Медіа прикріплено"
    await message.answer(f"Переглянь: {preview}", reply_markup=get_confirm_kb())
    await state.set_state(FeedbackStates.confirming)

@router.callback_query(F.data == "confirm_send", FeedbackStates.confirming)
async def confirm_send(callback: CallbackQuery, state: FSMContext, bot: Bot):  # bot inject в main
    data = await state.get_data()
    username = callback.from_user.username or "Без юзернейму"
    user_id = callback.from_user.id
    category = "новина"
    content = data.get('content', '')
    media = data.get('media')

    await notify_admins(bot, user_id, username, category, text=content, photo=media if isinstance(media, list) else None, document=media if hasattr(media, 'document') else None, video=media if hasattr(media, 'video') else None)

    await db.add_feedback(user_id, category, content)
    await callback.message.answer("Дякуємо! Твоя новина надіслана. ❤️")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_send", FeedbackStates.confirming)
async def cancel_send(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Відправка скасована. Почни заново з меню.", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()
