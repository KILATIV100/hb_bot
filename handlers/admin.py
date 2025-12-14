# handlers/admin.py
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
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

    # Get feedback from database
    feedback = await db.get_feedback(feedback_id)
    if not feedback:
        await callback.answer("❌ Заявку не знайдено в БД", show_alert=True)
        return

    # Send status "uploading..."
    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.UPLOAD_PHOTO)

    content = feedback["content"]
    caption_text = content if content != "Без тексту" else ""

    # Get media files
    media_records = await db.get_feedback_media(feedback_id)

    try:
        if not media_records:
            # Only text
            await bot.send_message(settings.CHANNEL_ID, caption_text)
        else:
            # Create album
            media_group = []

            # Determine if watermark is needed
            use_wm = (action == "wm")  # True if "With watermark" button was pressed

            for i, file_info in enumerate(media_records):
                # Process media with or without watermark
                input_media = await process_media_for_album(
                    bot=bot,
                    file_id=file_info['file_id'],
                    file_type=file_info['file_type'],
                    use_watermark=use_wm
                )

                # Add caption only to first file
                if i == 0 and caption_text:
                    input_media.caption = caption_text

                media_group.append(input_media)

            # Send to channel
            await bot.send_media_group(settings.CHANNEL_ID, media=media_group)

        # Update message for admin
        status = "✅ Опубліковано з лого" if action == "wm" else "🚀 Опубліковано оригінал"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(status)

    except Exception as e:
        await callback.answer(f"Помилка: {e}", show_alert=True)
        print(f"Publish error: {e}")

    await callback.answer()

# --- АДМІНСЬКІ КОМАНДИ ---

@router.message(Command('stats'))
async def cmd_stats(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return

    stats_day = await db.get_stats('day')
    stats_week = await db.get_stats('week')
    stats_all = await db.get_stats('all')

    day_str = "\n".join([f"{cat}: {count}" for cat, count in stats_day]) if stats_day else "Нема даних"
    week_str = "\n".join([f"{cat}: {count}" for cat, count in stats_week]) if stats_week else "Нема даних"
    all_str = "\n".join([f"{cat}: {count}" for cat, count in stats_all]) if stats_all else "Нема даних"

    response = (
        f"📊 Статистика бота:\n\n"
        f"📅 За сьогодні:\n{day_str}\n\n"
        f"🗓 За тиждень:\n{week_str}\n\n"
        f"📈 За весь час:\n{all_str}"
    )
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)

@router.message(Command('news'))
async def cmd_news_filter(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, username, content, timestamp FROM feedbacks WHERE category = 'новина' ORDER BY timestamp DESC LIMIT 20")
            rows = await cur.fetchall()

    if not rows:
        await message.answer("📰 Немає новин")
        return

    text = "📰 <b>ОСТАННІ НОВИНИ (макс 20):</b>\n\n"
    for row in rows:
        text += f"ID {row['id']} | @{row['username']}\n{row['content'][:100]}...\n\n"
    await message.answer(text)

@router.message(Command('ads'))
async def cmd_ads_filter(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, username, content, timestamp FROM feedbacks WHERE category = 'реклама' ORDER BY timestamp DESC LIMIT 20")
            rows = await cur.fetchall()

    if not rows:
        await message.answer("📢 Немає реклам")
        return

    text = "📢 <b>ОСТАННЯ РЕКЛАМА (макс 20):</b>\n\n"
    for row in rows:
        text += f"ID {row['id']} | @{row['username']}\n{row['content'][:100]}...\n\n"
    await message.answer(text)

@router.message(Command('other'))
async def cmd_other_filter(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, username, content, timestamp FROM feedbacks WHERE category = 'інше' ORDER BY timestamp DESC LIMIT 20")
            rows = await cur.fetchall()

    if not rows:
        await message.answer("💬 Немає інших повідомлень")
        return

    text = "💬 <b>ІНШІ ПОВІДОМЛЕННЯ (макс 20):</b>\n\n"
    for row in rows:
        text += f"ID {row['id']} | @{row['username']}\n{row['content'][:100]}...\n\n"
    await message.answer(text)

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

# Export router as admin_router for main.py
admin_router = router
