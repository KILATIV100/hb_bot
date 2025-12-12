# handlers/admin.py
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from states.feedback_states import AdminStates
from keyboards import get_quick_replies_kb
from config import settings
from database.db import db
from utils.watermark import add_watermark_and_send

admin_router = Router()

# Словник з готовими відповідями
QUICK_REPLIES = {
    "quick_reply_published": "✅ Дякуємо за участь! Новина вже на каналі.",
    "quick_reply_review": "⏳ Ваше повідомлення отримано. Розглядаємо.",
    "quick_reply_rejected": "❌ Дякуємо за час але Новина не відповідає критеріям.",
    "quick_reply_clarify": "❓ Дякуємо. Просимо уточнити джерело/деталі/спосіб звʼязку.",
}

# --- 🔥 ВІДПОВІДЬ СВАЙПОМ ---
@admin_router.message(F.reply_to_message & F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_reply_by_swipe(message: Message):
    """
    Дозволяє адміну відповісти користувачеві свайпом.
    """
    replied_msg = message.reply_to_message
    origin_text = replied_msg.text or replied_msg.caption or ""

    # Шукаємо ID
    match = re.search(r"\(ID:\s*(\d+)\)", origin_text)
    
    if not match:
        return

    target_user_id = int(match.group(1))
    
    try:
        await message.bot.send_message(
            target_user_id, 
            f"📬 <b>Відповідь від адміністратора:</b>\n\n{message.text}", 
            parse_mode=ParseMode.HTML
        )
        await message.answer(f"✅ Відповідь надіслана користувачу (ID: {target_user_id})!")

        last_feedback_id = await db.get_last_feedback_id(target_user_id)
        if last_feedback_id:
            await db.add_reply(last_feedback_id, message.from_user.id, message.text)

    except Exception as e:
        await message.answer(f"❌ Не вдалося надіслати відповідь: {e}")

# --- АДМІНСЬКІ КОМАНДИ ---

@admin_router.message(Command('stats'))
async def cmd_stats(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return

    stats_day = await db.get_stats('day')
    stats_week = await db.get_stats('week')
    stats_all = await db.get_stats('all')

    day_str = "\n".join([f"{cat}: {count}" for cat, count in stats_day]) if stats_day else "Нема"
    week_str = "\n".join([f"{cat}: {count}" for cat, count in stats_week]) if stats_week else "Нема"
    all_str = "\n".join([f"{cat}: {count}" for cat, count in stats_all]) if stats_all else "Нема"

    response = f"📊 Аналітика:\n\n📰 За день:\n{day_str}\n\n📆 За тиждень:\n{week_str}\n\n📋 За весь час:\n{all_str}"
    await message.answer(response)

@admin_router.message(Command('news'))
async def cmd_news_filter(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return
    async with db.conn.cursor() as cur:
        await cur.execute("SELECT id, username, content, timestamp FROM feedbacks WHERE category = 'новина' ORDER BY timestamp DESC LIMIT 20")
        rows = await cur.fetchall()

    if not rows:
        await message.answer("📰 Немає новин")
        return

    text = "📰 <b>ОСТАННІ НОВИНИ (макс 20):</b>\n\n"
    for row in rows:
        text += f"ID {row['id']} | @{row['username']}\n{row['content'][:100]}...\n\n"
    await message.answer(text)

@admin_router.message(Command('ads'))
async def cmd_ads_filter(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return
    async with db.conn.cursor() as cur:
        await cur.execute("SELECT id, username, content, timestamp FROM feedbacks WHERE category = 'реклама' ORDER BY timestamp DESC LIMIT 20")
        rows = await cur.fetchall()

    if not rows:
        await message.answer("📢 Немає реклам")
        return

    text = "📢 <b>ОСТАННЯ РЕКЛАМА (макс 20):</b>\n\n"
    for row in rows:
        text += f"ID {row['id']} | @{row['username']}\n{row['content'][:100]}...\n\n"
    await message.answer(text)

@admin_router.message(Command('other'))
async def cmd_other_filter(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS: return
    async with db.conn.cursor() as cur:
        await cur.execute("SELECT id, username, content, timestamp FROM feedbacks WHERE category = 'інше' ORDER BY timestamp DESC LIMIT 20")
        rows = await cur.fetchall()

    if not rows:
        await message.answer("💬 Немає інших повідомлень")
        return

    text = "💬 <b>ІНШІ ПОВІДОМЛЕННЯ (макс 20):</b>\n\n"
    for row in rows:
        text += f"ID {row['id']} | @{row['username']}\n{row['content'][:100]}...\n\n"
    await message.answer(text)

# --- CALLBACKS ---

@admin_router.callback_query(F.data.startswith("reply_to_"))
async def reply_to_feedback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Тільки для адмінів! 🚫", show_alert=True)
        return

    feedback_id = int(callback.data.replace("reply_to_", ""))
    feedback = await db.get_feedback(feedback_id)

    if not feedback:
        await callback.answer("Feedback не знайдено!", show_alert=True)
        return

    await state.set_state(AdminStates.replying)
    await state.update_data(feedback_id=feedback_id, replying_to=feedback["user_id"], username=feedback["username"])

    await callback.message.answer(
        f"💬 <b>Відповідь для @{feedback['username']}</b>\n\n"
        f"📝 Його повідомлення: <code>{feedback['content']}</code>\n\n"
        f"Обери готову відповідь або напиши свою:",
        reply_markup=get_quick_replies_kb()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("publish_to_"))
async def publish_to_channel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Тільки для адмінів! 🚫", show_alert=True)
        return

    feedback_id = int(callback.data.replace("publish_to_", ""))
    feedback = await db.get_feedback(feedback_id)

    if not feedback:
        await callback.answer("Feedback не знайдено!", show_alert=True)
        return

    if feedback.get('photo_file_id'):
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        watermark_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ З вотермаркою", callback_data=f"publish_with_wm_{feedback_id}"),
                InlineKeyboardButton(text="❌ Без вотермарки", callback_data=f"publish_no_wm_{feedback_id}")
            ]
        ])
        await callback.message.answer("🎨 Додати логотип XBrovary на фото?", reply_markup=watermark_kb)
        await callback.answer()
        return

    await do_publish_feedback(callback, feedback_id, feedback, use_watermark=False)

@admin_router.callback_query(F.data.startswith("publish_with_wm_"))
async def publish_with_watermark(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS: return
    feedback_id = int(callback.data.replace("publish_with_wm_", ""))
    feedback = await db.get_feedback(feedback_id)
    if feedback: await do_publish_feedback(callback, feedback_id, feedback, use_watermark=True)

@admin_router.callback_query(F.data.startswith("publish_no_wm_"))
async def publish_without_watermark(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS: return
    feedback_id = int(callback.data.replace("publish_no_wm_", ""))
    feedback = await db.get_feedback(feedback_id)
    if feedback: await do_publish_feedback(callback, feedback_id, feedback, use_watermark=False)

async def do_publish_feedback(callback: CallbackQuery, feedback_id: int, feedback: dict, use_watermark: bool):
    publish_text = f"#нампишуть\n\n{feedback['content']}"
    try:
        if feedback.get('photo_file_id'):
            if use_watermark:
                await add_watermark_and_send(callback.bot, feedback['photo_file_id'], publish_text, ParseMode.HTML)
            else:
                await callback.bot.send_photo(settings.CHANNEL_ID, feedback['photo_file_id'], caption=publish_text, parse_mode=ParseMode.HTML)
        elif feedback.get('video_file_id'):
            await callback.bot.send_video(settings.CHANNEL_ID, feedback['video_file_id'], caption=publish_text, parse_mode=ParseMode.HTML)
        elif feedback.get('document_file_id'):
            await callback.bot.send_document(settings.CHANNEL_ID, feedback['document_file_id'], caption=publish_text, parse_mode=ParseMode.HTML)
        else:
            await callback.bot.send_message(settings.CHANNEL_ID, publish_text, parse_mode=ParseMode.HTML)

        await callback.answer("✅ Опубліковано на канал!", show_alert=True)
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>ОПУБЛІКОВАНО НА КАНАЛ</b>")
    except Exception as e:
        await callback.answer(f"❌ Помилка при публікації: {e}", show_alert=True)

@admin_router.callback_query(F.data.startswith("quick_reply_"))
async def quick_reply(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS: return
    data = await state.get_data()
    feedback_id = data.get("feedback_id")
    user_id = data.get("replying_to")
    if not user_id or not feedback_id:
        await callback.answer("Помилка даних", show_alert=True)
        return

    reply_type = callback.data
    if reply_type == "quick_reply_custom":
        await callback.message.answer("💬 Напиши свою відповідь для користувача:")
        await callback.answer()
        return

    reply_text = QUICK_REPLIES.get(reply_type, "Error")
    await db.add_reply(feedback_id, callback.from_user.id, reply_text)
    try:
        await callback.bot.send_message(user_id, f"📬 <b>Адмін відповив:</b>\n\n{reply_text}", parse_mode=ParseMode.HTML)
        await callback.message.answer("✅ Відповідь надіслана!")
    except Exception as e:
        await callback.message.answer(f"❌ Помилка: {e}")
    await state.clear()
    await callback.answer()

@admin_router.message(F.text, AdminStates.replying)
async def send_custom_reply(message: Message, state: FSMContext):
    if message.from_user.id not in settings.ADMIN_IDS: return
    data = await state.get_data()
    feedback_id = data.get("feedback_id")
    user_id = data.get("replying_to")
    if not user_id: return
    await db.add_reply(feedback_id, message.from_user.id, message.text)
    try:
        await message.bot.send_message(user_id, f"📬 <b>Адмін відповив:</b>\n\n{message.text}", parse_mode=ParseMode.HTML)
        await message.answer("✅ Відповідь надіслана!")
    except Exception as e:
        await message.answer(f"❌ Помилка: {e}")
    await state.clear()

# --- ⛔️ БЛОКУВАННЯ СПАМУ ВІД АДМІНІВ ⛔️ ---
# Цей хендлер стоїть останнім і ловить ВСЕ від адмінів, що не обробилось вище
# Тобто: якщо це не команда, не свайп, не натискання кнопки -> просто ігноруємо
@admin_router.message(F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_prevent_spam(message: Message):
    """
    Пастка для повідомлень адміна, щоб вони не потрапляли в базу як 'feedback'.
    """
    # Ми нічого не робимо (pass), але оскільки хендлер спрацював,
    # повідомлення не піде далі до користувацьких хендлерів.
    pass
