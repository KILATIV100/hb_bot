#!/usr/bin/env python3
"""Тестовий скрипт для перевірки змінних середовища"""

import os
import sys

print("=== Перевірка змінних середовища ===\n")

# Перевіряємо сирі змінні
print("1. Сирі змінні з os.environ:")
print(f"BOT_TOKEN: {os.getenv('BOT_TOKEN', 'НЕ ЗНАЙДЕНО')}")
print(f"CHANNEL_ID: {os.getenv('CHANNEL_ID', 'НЕ ЗНАЙДЕНО')}")
print(f"ADMIN_IDS: {os.getenv('ADMIN_IDS', 'НЕ ЗНАЙДЕНО')}")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'НЕ ЗНАЙДЕНО')[:50]}..." if os.getenv('DATABASE_URL') else "DATABASE_URL: НЕ ЗНАЙДЕНО")

print("\n2. Спроба завантажити через pydantic_settings:")
try:
    from config import settings
    print(f"✅ BOT_TOKEN: {settings.BOT_TOKEN[:20]}...")
    print(f"✅ CHANNEL_ID: {settings.CHANNEL_ID}")
    print(f"✅ ADMIN_IDS: {settings.ADMIN_IDS}")
    print(f"✅ DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    print("\n🎉 Всі змінні завантажені успішно!")
except Exception as e:
    print(f"❌ ПОМИЛКА: {e}")
    print(f"Тип помилки: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
