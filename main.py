# main.py
import asyncio
import logging
import sys
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

async def main():
    # Налаштування логування
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Підключення до БД
    await db.connect()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Реєстрація роутерів
    dp.include_routers(admin_router, start_router, news_router, ad_router, other_router)

    # Очищення вебхуків та очікуваних апдейтів перед запуском
    # Це допомагає уникнути конфліктів при перезапуску
    await bot.delete_webhook(drop_pending_updates=True)

    print("🚀 Бот успішно запущений! Старі сесії очищено.")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Помилка при polling: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот зупинено користувачем")
