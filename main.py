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
    # Налаштування логування: додаємо час і рівень важливості
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)

    logger.info("🚀 Ініціалізація бота...")

    # Підключення до БД
    try:
        await db.connect()
    except Exception as e:
        logger.critical(f"❌ Критична помилка підключення до БД: {e}")
        # Без бази бот не має сенсу, тому зупиняємо
        return

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Підключення роутерів (порядок важливий!)
    # Спочатку admin (щоб перехоплювати команди адміна), потім інші
    dp.include_routers(admin_router, start_router, news_router, ad_router, other_router)

    logger.info("🗑️ Очищення черги старих оновлень...")
    # Це критично важливо, якщо бот довго не працював або "завис"
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("✅ Бот запущений! Очікую повідомлень...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Помилка в процесі роботи (polling): {e}")
    finally:
        # Коректне завершення роботи
        if hasattr(db, 'pool') and db.pool:
            await db.pool.close()
            logger.info("🛑 З'єднання з БД закрито.")
        logger.info("👋 Бот зупинений.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот вимкнений вручну (Ctrl+C)")
