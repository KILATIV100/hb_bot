# utils/notify_admins.py
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.utils.media_group import MediaGroupBuilder
from config import settings

logger = logging.getLogger(__name__)

async def notify_admins(
    bot: Bot,
    user_id: int,
    username: str,
    category: str,
    feedback_id: int | None = None,
    text: str | None = None,
    photo=None,
    document=None,
    video=None,
    media_files: list = None,
    is_anonymous: bool = False,
) -> None:
    """Надсилає повідомлення адмінам з вибором варіанту публікації"""
    from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument

    username = username or "Без юзернейму"

    # 3. Заголовок з категорією відповідно до кнопки
    category_labels = {
        "новина": ("📰", "Нова НОВИНА"),
        "реклама": ("📢", "Новий запит на РЕКЛАМУ"),
        "інше": ("💬", "Нове повідомлення")
    }
    emoji, label = category_labels.get(category, ("📨", "Новий ЗАПИТ"))

    if is_anonymous:
        user_info = f"{emoji} <b>{label} (👻 АНОНІМНО)</b>\n\n"
    else:
        user_info = f"{emoji} <b>{label}</b> від @{username} (ID: <code>{user_id}</code>)\n\n"

    if text:
        user_info += text

    # Кнопки для адміна: Вибір публікації
    admin_kb = None
    if feedback_id:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                # 1. Вибір: з вотермаркою або без
                InlineKeyboardButton(text="✅ З водяним", callback_data=f"pub_wm_{feedback_id}"),
                InlineKeyboardButton(text="🚀 Оригінал", callback_data=f"pub_orig_{feedback_id}")
            ],
            [
                InlineKeyboardButton(text="💬 Відповісти", callback_data=f"reply_to_{feedback_id}"),
                InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{feedback_id}")
            ]
        ])

    successful_sends = 0
    
    # 2. Сповіщення йдуть в приватні повідомлення (в бот)
    for admin_id in settings.ADMIN_IDS:
        try:
            # Логіка відправки альбому
            if media_files and len(media_files) > 0:
                media_group = []
                for i, m in enumerate(media_files):
                    if m['type'] == 'photo':
                        media = InputMediaPhoto(media=m['file_id'])
                    elif m['type'] == 'video':
                        media = InputMediaVideo(media=m['file_id'])
                    elif m['type'] == 'document':
                        media = InputMediaDocument(media=m['file_id'])
                    else:
                        continue

                    if i == 0:
                        media.caption = user_info
                        media.parse_mode = ParseMode.HTML

                    media_group.append(media)

                await bot.send_media_group(admin_id, media=media_group)
                if admin_kb:
                    await bot.send_message(admin_id, "⬆️ Оберіть дію:", reply_markup=admin_kb)
            
            # Логіка для поодиноких файлів (legacy)
            elif photo:
                await bot.send_photo(admin_id, photo[-1].file_id, caption=user_info,
                                   parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            elif video:
                await bot.send_video(admin_id, video.file_id, caption=user_info,
                                   parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            else:
                await bot.send_message(admin_id, user_info, reply_markup=admin_kb,
                                     parse_mode=ParseMode.HTML)
            
            successful_sends += 1
        except Exception as e:
            logger.error(f"⚠️ Не вдалося надіслати адміну {admin_id}: {e}")

    if successful_sends == 0:
        logger.warning("❌ Жоден адмін не отримав повідомлення!")
