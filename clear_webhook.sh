#!/bin/bash
# Скрипт для видалення webhook через Telegram API

# Замініть YOUR_BOT_TOKEN на ваш токен
BOT_TOKEN="${BOT_TOKEN:-YOUR_BOT_TOKEN}"

echo "🔍 Перевірка webhook..."
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | jq .

echo ""
echo "🗑️  Видалення webhook..."
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"

echo ""
echo "✅ Готово! Тепер можна запускати бота в polling режимі"
