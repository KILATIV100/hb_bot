# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.feedback_states import AdminStates
from config import settings
from database.db import db

admin_router = Router()

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

@admin_router.callback_query(F.data.startswith("reply_to_"))
async def reply_to_feedback(callback: CallbackQuery, state: FSMContext):
    """Обробник для кнопки 'Ответити'"""
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
        f"💬 Напиши відповідь для юзера @{feedback['username']}:\n\n"
        f"📝 Його повідомлення: {feedback['content']}"
    )
    await callback.answer()

@admin_router.message(F.text, AdminStates.replying)
async def send_reply(message: Message, state: FSMContext):
    """Обробник для надсилання відповіді користувачу"""
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
            f"📬 <b>Адмін відповів на твоє повідомлення!</b>\n\n{message.text}"
        )
        await message.answer(f"✅ Відповідь надіслана юзеру @{username}!")
    except Exception as e:
        await message.answer(f"❌ Помилка при надсиланні: {e}")

    await state.clear()
