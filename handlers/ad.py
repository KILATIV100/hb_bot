from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.feedback_states import FeedbackStates
from utils.notify_admins import notify_admins
from keyboards import get_anonymity_kb, get_confirm_kb, get_main_menu_kb
from database.db import db

router = Router()

@router.message(F.text.in_(["📢 Запит про рекламу", "Запит про рекламу"]))
async def start_ad(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 5 хвилин перед наступною відправкою 🚫")
        return
    await state.set_state(FeedbackStates.choosing_anonymity)
    await state.update_data(feedback_type="ad")
    await message.answer(
        "Як ти хочеш, щоб твій запит був відправлений?",
        reply_markup=get_anonymity_kb()
    )

@router.callback_query(F.data.in_(["anonymous_yes", "anonymous_no"]), FeedbackStates.choosing_anonymity)
async def choose_anonymity_ad(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("feedback_type") != "ad":
        return

    is_anonymous = callback.data == "anonymous_yes"
    await state.update_data(is_anonymous=is_anonymous)
    await state.set_state(FeedbackStates.waiting_for_ad)

    if is_anonymous:
        await callback.message.edit_text("👻 Чудово! Тепер надішли запит про рекламу (текст + фото/відео/файл):")
    else:
        await callback.message.edit_text("👤 Чудово! Тепер надішли запит про рекламу (текст + фото/відео/файл):")
    await callback.answer()

@router.message(FeedbackStates.waiting_for_ad)
async def receive_ad(message: Message, state: FSMContext):
    await state.update_data(
        content=message.text or "Без тексту",
        media=message.photo or message.document or message.video
    )
    preview = message.text or "[Медіа]"
    await message.answer(f"Перевірно?\n\n{preview}", reply_markup=get_confirm_kb())
    await state.set_state(FeedbackStates.confirming)

@router.callback_query(F.data == "confirm_send", FeedbackStates.confirming)
async def confirm_ad(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    username = callback.from_user.username or "Без імені"
    is_anonymous = data.get("is_anonymous", False)

    # Отримуємо file_id медіа
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

    # Спочатку додаємо в БД і отримуємо feedback_id
    feedback_id = await db.add_feedback(callback.from_user.id, username, "реклама", data["content"],
                                       photo_file_id=photo_file_id, video_file_id=video_file_id,
                                       document_file_id=document_file_id)

    # Потім повідомляємо адмінів з feedback_id
    await notify_admins(
        bot=bot,
        user_id=callback.from_user.id,
        username=username,
        category="реклама",
        feedback_id=feedback_id,
        text=data["content"],
        photo=data.get("media") if isinstance(data.get("media"), list) else None,
        document=data.get("media") if hasattr(data.get("media", {}), 'file_id') and not isinstance(data.get("media"), list) else None,
        video=data.get("media") if hasattr(data.get("media", {}), 'file_id') else None,
        is_anonymous=is_anonymous
    )

    await callback.message.answer("Дякуємо! Запит про рекламу надіслано ❤️", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_send")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Скасовано. Обери дію:", reply_markup=get_main_menu_kb())
    await state.clear()
    await callback.answer()
