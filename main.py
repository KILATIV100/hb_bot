# main.py (async db connect, bot inject)
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from database.db import db
from handlers.start import router as start_router
from handlers.news import router as news_router
# Додай: from handlers.ad import router as ad_router
# from handlers.other import router as other_router
from handlers.admin import admin_router

async def main():
    logging.basicConfig(level=logging.INFO)
    await db.connect()  # Підключаємо DB

    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers
    dp.include_routers(start_router, news_router, admin_router)  # + ad, other

    # Middleware для bot в handlers, якщо треба (але в callback ми передаємо bot вручну)

    print("Бот для новин запущений на Railway! 🔥 DB connected, чекаю трафік.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
