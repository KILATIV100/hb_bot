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
    await db.connect()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(start_router, news_router, ad_router, other_router, admin_router)

    print("Бот для новинного каналу запущений! Аналітика + UI/UX — все на рівні.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
