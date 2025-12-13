# handlers/admin.py
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from database.db import db
from config import settings
from utils.watermark import process_media_for_album
from states.feedback_states import AdminStates

router = Router()

# --- ПУБЛІКАЦІЯ ---

@router.callback_query(F.data.startswith("pub_"))
async def handle_publish(callback: CallbackQuery, bot: Bot):
    """
    Обробляє обидві кнопки публікації:
    pub_wm_ID   -> З водяним знаком
    pub_orig_ID -> Без водяного знаку (оригінал)
    """
    action, feedback_id = callback.data.split("_")[1], callback.data.split("_")[2]
    feedback_id = int(feedback_id)
    
    # Отримуємо дані з БД
    feedback = await db.get_feedback(feedback_id)
    if not feedback:
        await callback.answer("❌ Заявку не знайдено в БД", show_alert=True)
        return

    # Відправляємо статус "uploading...", бо це може зайняти час
    # (Це вирішує п.4 - адмін бачить, що процес іде)
    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    content = feedback["content"]
    # Якщо контент "Без тексту", прибираємо його для каналу, або лишаємо пустим
    caption_text = content if content != "Без тексту" else ""

    # Отримуємо медіафайли
    media_records = await db.get_feedback_media(feedback_id)
    
    try:
        if not media_records:
            # Тільки текст
            await bot.send_message(settings.CHANNEL_ID, caption_text)
        else:
            # Формуємо альбом
            media_group = []
            
            # Визначаємо, чи потрібна вотермарка
            use_wm = (action == "wm") # True якщо натиснули "З водяним"

            for i, file_info in enumerate(media_records):
                # Викликаємо функцію з utils/watermark.py
                # Вона сама вирішить: качати і обробляти (якщо use_wm=True)
                # чи просто повернути file_id (якщо use_wm=False)
                input_media = await process_media_for_album(
                    bot=bot,
                    file_id=file_info['file_id'],
                    file_type=file_info['file_type'],
                    use_watermark=use_wm 
                )
                
                # Підпис тільки до першого файлу
                if i == 0 and caption_text:
                    input_media.caption = caption_text

                media_group.append(input_media)

            # Відправляємо в канал
            await bot.send_media_group(settings.CHANNEL_ID, media=media_group)

        # Оновлюємо повідомлення у адміна
        status = "✅ Опубліковано з лого" if action == "wm" else "🚀 Опубліковано оригінал"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(status)
        
    except Exception as e:
        await callback.answer(f"Помилка: {e}", show_alert=True)
        print(f"Publish error: {e}")

    await callback.answer()

# --- ВІДПОВІДЬ КОРИСТУВАЧУ ---

@router.callback_query(F.data.startswith("reply_to_"))
async def start_reply(callback: CallbackQuery, state: FSMContext):
    feedback_id = int(callback.data.split("_")[2])
    await state.update_data(current_feedback_id=feedback_id)
    await state.set_state(AdminStates.replying)
    await callback.message.answer("✍️ Напишіть текст відповіді для користувача:")
    await callback.answer()

@router.message(AdminStates.replying)
async def send_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    feedback_id = data.get("current_feedback_id")
    
    feedback = await db.get_feedback(feedback_id)
    if feedback:
        user_id = feedback["user_id"]
        try:
            await bot.send_message(
                user_id, 
                f"🔔 <b>Відповідь від адміністратора:</b>\n\n{message.text}",
                parse_mode="HTML"
            )
            await message.answer("✅ Відповідь надіслано!")
            await db.add_reply(feedback_id, message.from_user.id, message.text)
        except Exception as e:
            await message.answer(f"❌ Не вдалося надіслати (можливо, бот заблокований): {e}")
    
    await state.clear()

# --- ВІДХИЛЕННЯ ---

@router.callback_query(F.data.startswith("reject_"))
async def reject_post(callback: CallbackQuery):
    await callback.message.edit_text(f"{callback.message.text}\n\n❌ <b>ВІДХИЛЕНО</b>", parse_mode="HTML", reply_markup=None)
    await callback.answer("Відхилено")
