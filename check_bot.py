#!/usr/bin/env python3
"""
Скрипт для діагностики проблем з ботом
Перевіряє стан webhook та видаляє його якщо потрібно
"""

import asyncio
from aiogram import Bot
from config import settings

async def check_bot_status():
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        print("🔍 Перевірка статусу бота...")

        # Отримуємо інформацію про бота
        me = await bot.get_me()
        print(f"✅ Бот: @{me.username} (ID: {me.id})")

        # Перевіряємо webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n📡 Webhook Info:")
        print(f"  URL: {webhook_info.url or 'Не встановлено'}")
        print(f"  Pending updates: {webhook_info.pending_update_count}")
        print(f"  Last error: {webhook_info.last_error_message or 'Немає'}")

        if webhook_info.url:
            print("\n⚠️  Webhook активний! Це може викликати конфлікт з polling.")
            confirm = input("Видалити webhook? (y/n): ")
            if confirm.lower() == 'y':
                await bot.delete_webhook(drop_pending_updates=True)
                print("✅ Webhook видалено!")
            else:
                print("❌ Webhook залишився. Бот може не працювати через конфлікт.")
        else:
            print("✅ Webhook не встановлено - все гаразд для polling режиму")

        # Перевіряємо можливість отримання оновлень
        print("\n🔄 Тест отримання оновлень...")
        try:
            updates = await bot.get_updates(limit=1, timeout=5)
            print(f"✅ Отримано {len(updates)} оновлень")
        except Exception as e:
            print(f"❌ Помилка: {e}")
            if "Conflict" in str(e):
                print("\n🚨 КОНФЛІКТ: Інший екземпляр бота вже запущений!")
                print("   Рішення:")
                print("   1. Зупиніть всі інші екземпляри бота")
                print("   2. Перезапустіть контейнер/сервіс")
                print("   3. Зачекайте 2-3 хвилини і спробуйте знову")

    except Exception as e:
        print(f"❌ Критична помилка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(check_bot_status())
