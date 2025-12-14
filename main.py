import asyncio
import logging
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
    logging.basicConfig(level=logging.INFO)
    
    # Підключаємось до БД
    await db.connect()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Реєструємо роутери
    dp.include_routers(admin_router, start_router, news_router, ad_router, other_router)

    print("Бот для новинного каналу запущений! Аналітика + UI/UX — все на рівні.")
    
    try:
        # Запуск поллінгу
        await dp.start_polling(bot)
    finally:
        # Коректне завершення роботи
        print("Зупинка бота...")
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот зупинений.")
