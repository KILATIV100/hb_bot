# utils/notify_admins.py (async, без змін)
from aiogram import Bot
from config import settings

# utils/notify_admins.py — заміни цей рядок:
await notify_admins(bot, user_id, username, category, text=content, photo=media if isinstance(media, list) else None, document=media if hasattr(media, 'document') else None, video=media if hasattr(media, 'video') else None)

# на цей простіший і 100% робочий:
if isinstance(media, list):  # це фото
    await notify_admins(bot, user_id, username, category, text=content, photo=media)
elif media and hasattr(media, 'mime_type') and media.mime_type.startswith('video'):
    await notify_admins(bot, user_id, username, category, text=content, video=media)
elif media:
    await notify_admins(bot, user_id, username, category, text=content, document=media)
else:
    user_info = f"Новий {category} від @{username} (ID: {user_id})\n\n"
    if text:
        user_info += text

    for admin_id in settings.ADMIN_IDS:
        try:
            if photo:
                await bot.send_photo(admin_id, photo[-1].file_id, caption=user_info)
            elif document:
                await bot.send_document(admin_id, document.file_id, caption=user_info)
            elif video:
                await bot.send_video(admin_id, video.file_id, caption=user_info)
            else:
                await bot.send_message(admin_id, user_info)
        except Exception as e:
            print(f"Помилка для адміна {admin_id}: {e}")

    # В чат логів
    try:
        if photo:
            await bot.send_photo(settings.FEEDBACK_CHAT_ID, photo[-1].file_id, caption=user_info)
        elif document:
            await bot.send_document(settings.FEEDBACK_CHAT_ID, document.file_id, caption=user_info)
        elif video:
            await bot.send_video(settings.FEEDBACK_CHAT_ID, video.file_id, caption=user_info)
        else:
            await bot.send_message(settings.FEEDBACK_CHAT_ID, user_info)
    except Exception as e:
        print(f"Помилка для чату логів: {e}")
