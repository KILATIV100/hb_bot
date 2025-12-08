# handlers/admin.py (async stats)
from aiogram import Router, F, Bot   # ← головне — додати Bot сюди
from aiogram.types import Message, CallbackQuery
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
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

    response = f"📊 Аналітика:\n\nЗа день:\n{day_str}\n\nЗа тиждень:\n{week_str}\n\nЗа весь час:\n{all_str}"
    await message.answer(response)
