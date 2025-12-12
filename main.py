import asyncio
import logging
import sys
import os
import shutil  # Для видалення папки
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.db import db
from handlers import start, news, ad, other, admin

# Налаштування логування
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def init_db():
    """Ініціалізація бази даних"""
    await db.connect()
    await db.create_tables()
    print("✅ База даних підключена та перевірена.")

def clean_temp_folder():
    """Повне очищення тимчасової папки при старті"""
    temp_dir = os.path.join(os.path.dirname(__file__), "utils", "temp")
    # Або просто "temp", залежно від того, де вона створюється у watermark.py
    # В watermark.py: BASE_DIR/temp. Отже, тут:
    base_dir = os.path.dirname(__file__)
    temp_dir = os.path.join(base_dir, "temp")

    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir) # Видаляємо папку з усім вмістом
            print(f"🧹 Папка {temp_dir} успішно видалена.")
        except Exception as e:
            print(f"❌ Помилка при видаленні temp: {e}")
    
    # Створюємо чисту папку
    os.makedirs(temp_dir, exist_ok=True)
    print(f"✨ Створено чисту папку: {temp_dir}")

async def main():
    # 1. Запуск БД
    await init_db()
    
    # 2. Очищення сміття
    clean_temp_folder()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Реєстрація роутерів
    dp.include_router(start.router)
    dp.include_router(news.router)
    dp.include_router(ad.router)
    dp.include_router(other.router)
    dp.include_router(admin.admin_router)

    print("🚀 Бот запущено!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот зупинений")
