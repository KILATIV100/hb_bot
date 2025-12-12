# main.py
import asyncio
import logging
import sys
import os
import shutil
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.db import db

# Роутери
from handlers.start import router as start_router
from handlers.news import router as news_router
from handlers.ad import router as ad_router
from handlers.other import router as other_router
from handlers.admin import admin_router

# 👇 Імпортуємо наш новий Middleware
from utils.album_middleware import AlbumMiddleware

async def init_db():
    await db.connect()
    await db.create_tables()

def clean_temp_folder():
    base_dir = os.path.dirname(__file__)
    temp_dir = os.path.join(base_dir, "temp") # або utils/temp залежно від налаштувань
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    os.makedirs(temp_dir, exist_ok=True)

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await init_db()
    clean_temp_folder()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 👇 ПІДКЛЮЧАЄМО MIDDLEWARE ТУТ
    # Воно буде працювати для всіх повідомлень
    dp.message.middleware(AlbumMiddleware(latency=0.5))

    dp.include_routers(admin_router, start_router, news_router, ad_router, other_router)

    print("🚀 Бот запущено з підтримкою альбомів!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот зупинений")
