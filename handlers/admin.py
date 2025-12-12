# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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

@admin_router.message(Command('stats'))
async def cmd_stats(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("Тільки для адмінів! 🚫")
        return

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
    """Фільтр новин для адмінів"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return

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
    """Фільтр реклами для адмінів"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return

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
    """Фільтр інших повідомлень для адмінів"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return

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

@admin_router.callback_query(F.data.startswith("reply_to_"))
async def reply_to_feedback(callback: CallbackQuery, state: FSMContext):
    """Обробник для кнопки 'Відповісти' з приватного чату адміна"""
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

    # Відправляємо меню в приватний чат адміну
    await callback.message.answer(
        f"💬 <b>Відповідь для @{feedback['username']}</b>\n\n"
        f"📝 Його повідомлення: <code>{feedback['content']}</code>\n\n"
        f"Обери готову відповідь або напиши свою:",
        reply_markup=get_quick_replies_kb()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("publish_to_"))
async def publish_to_channel(callback: CallbackQuery, state: FSMContext):
    """Обробник для кнопки 'Опублікувати' з приватного чату адміна"""
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Тільки для адмінів! 🚫", show_alert=True)
        return

    feedback_id = int(callback.data.replace("publish_to_", ""))
    feedback = await db.get_feedback(feedback_id)

    if not feedback:
        await callback.answer("Feedback не знайдено!", show_alert=True)
        return

    # Якщо є фото - запитуємо про водяний знак
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

    # Якщо немає фото - публікуємо одразу
    await do_publish_feedback(callback, feedback_id, feedback, use_watermark=False)


@admin_router.callback_query(F.data.startswith("publish_with_wm_"))
async def publish_with_watermark(callback: CallbackQuery):
    """Публікує з вотермаркою"""
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Тільки для адмінів! 🚫", show_alert=True)
        return

    feedback_id = int(callback.data.replace("publish_with_wm_", ""))
    feedback = await db.get_feedback(feedback_id)

    if not feedback:
        await callback.answer("Feedback не знайдено!", show_alert=True)
        return

    await do_publish_feedback(callback, feedback_id, feedback, use_watermark=True)


@admin_router.callback_query(F.data.startswith("publish_no_wm_"))
async def publish_without_watermark(callback: CallbackQuery):
    """Публікує без вотермарки"""
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Тільки для адмінів! 🚫", show_alert=True)
        return

    feedback_id = int(callback.data.replace("publish_no_wm_", ""))
    feedback = await db.get_feedback(feedback_id)

    if not feedback:
        await callback.answer("Feedback не знайдено!", show_alert=True)
        return

    await do_publish_feedback(callback, feedback_id, feedback, use_watermark=False)


async def do_publish_feedback(callback: CallbackQuery, feedback_id: int, feedback: dict, use_watermark: bool):
    """Виконує публікацію з або без вотермарки"""
    # Формуємо текст для публікації з префіксом #нампишуть
    publish_text = f"#нампишуть\n\n{feedback['content']}"

    try:
        # Публікуємо на основний канал з медіа (якщо є)
        if feedback.get('photo_file_id'):
            if use_watermark:
                # Додаємо водяний знак до фото
                await add_watermark_and_send(
                    callback.bot,
                    feedback['photo_file_id'],
                    publish_text,
                    ParseMode.HTML
                )
            else:
                # Публікуємо без вотермарки
                await callback.bot.send_photo(
                    settings.CHANNEL_ID,
                    feedback['photo_file_id'],
                    caption=publish_text,
                    parse_mode=ParseMode.HTML
                )
        elif feedback.get('video_file_id'):
            await callback.bot.send_video(
                settings.CHANNEL_ID,
                feedback['video_file_id'],
                caption=publish_text,
                parse_mode=ParseMode.HTML
            )
        elif feedback.get('document_file_id'):
            await callback.bot.send_document(
                settings.CHANNEL_ID,
                feedback['document_file_id'],
                caption=publish_text,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.bot.send_message(
                settings.CHANNEL_ID,
                publish_text,
                parse_mode=ParseMode.HTML
            )

        await callback.answer("✅ Опубліковано на канал!", show_alert=True)
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>ОПУБЛІКОВАНО НА КАНАЛ</b>"
        )
    except Exception as e:
        await callback.answer(f"❌ Помилка при публікації: {e}", show_alert=True)

@admin_router.callback_query(F.data.startswith("quick_reply_"))
async def quick_reply(callback: CallbackQuery, state: FSMContext):
    """Обробник для готових відповідей"""
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("Тільки для адмінів! 🚫", show_alert=True)
        return

    data = await state.get_data()
    feedback_id = data.get("feedback_id")
    user_id = data.get("replying_to")
    username = data.get("username")

    if not user_id or not feedback_id:
        await callback.answer("Помилка: невідома інформація про feedback", show_alert=True)
        return

    reply_type = callback.data

    if reply_type == "quick_reply_custom":
        await callback.message.answer("💬 Напиши свою відповідь для користувача:")
        await callback.answer()
        return

    # Отримуємо готову відповідь
    reply_text = QUICK_REPLIES.get(reply_type, "Помилка: невідома відповідь")

    # Зберігаємо в БД
    reply_id = await db.add_reply(feedback_id, callback.from_user.id, reply_text)

    # Відправляємо користувачу
    try:
        await callback.bot.send_message(
            user_id,
            f"📬 <b>Адмін відповив на твоє повідомлення!</b>\n\n{reply_text}",
            parse_mode=ParseMode.HTML
        )
        await callback.message.answer(f"✅ Відповідь надіслана юзеру @{username}!")
    except Exception as e:
        await callback.message.answer(f"❌ Помилка при надсиланні: {e}")

    await state.clear()
    await callback.answer()

@admin_router.message(F.text, AdminStates.replying)
async def send_custom_reply(message: Message, state: FSMContext):
    """Обробник для користувацької відповіді"""
    if message.from_user.id not in settings.ADMIN_IDS:
        return

    data = await state.get_data()
    feedback_id = data.get("feedback_id")
    user_id = data.get("replying_to")
    username = data.get("username")

    if not user_id or not feedback_id:
        await message.answer("❌ Помилка: невідома інформація про feedback")
        return

    # Зберігаємо відповідь в БД
    reply_id = await db.add_reply(feedback_id, message.from_user.id, message.text)

    # Відправляємо відповідь користувачу
    try:
        await message.bot.send_message(
            user_id,
            f"📬 <b>Адмін відповив на твоє повідомлення!</b>\n\n{message.text}",
            parse_mode=ParseMode.HTML
        )
        await message.answer(f"✅ Відповідь надіслана юзеру @{username}!")
    except Exception as e:
        await message.answer(f"❌ Помилка при надсиланні: {e}")

    await state.clear()
