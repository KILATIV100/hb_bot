#!/usr/bin/env python3
"""Швидкий тест з'єднання з Telegram Bot API"""

import asyncio
import sys

async def test_bot():
    print("=== Тест Telegram Bot ===\n")

    # 1. Перевірка змінних
    print("1️⃣ Перевірка змінних середовища...")
    try:
        from config import settings
        print(f"   ✅ BOT_TOKEN: {settings.BOT_TOKEN[:20]}...")
        print(f"   ✅ CHANNEL_ID: {settings.CHANNEL_ID}")
        print(f"   ✅ ADMIN_IDS: {settings.ADMIN_IDS}")
        print(f"   ✅ DATABASE_URL: налаштований\n")
    except Exception as e:
        print(f"   ❌ Помилка конфігурації: {e}")
        return False

    # 2. Тест Bot API
    print("2️⃣ Перевірка з'єднання з Telegram Bot API...")
    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        me = await bot.get_me()
        print(f"   ✅ Бот успішно підключений!")
        print(f"   📱 Ім'я бота: @{me.username}")
        print(f"   🆔 ID бота: {me.id}")
        print(f"   👤 Ім'я: {me.first_name}\n")

        await bot.session.close()
        return True

    except Exception as e:
        print(f"   ❌ Помилка підключення до Bot API: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_bot())
        if result:
            print("🎉 Всі тести пройдені успішно!")
            sys.exit(0)
        else:
            print("❌ Є проблеми з конфігурацією")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Тест перервано")
        sys.exit(1)
