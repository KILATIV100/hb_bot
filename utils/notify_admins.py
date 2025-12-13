# utils/notify_admins.py
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
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
    is_anonymous: bool = False,
) -> None:
    """Надсилає повідомлення всім адмінам в приватні чати з кнопками"""
    username = username or "Без юзернейму"

    category_labels = {
        "новина": ("📰", "Нова НОВИНА"),
        "реклама": ("📢", "Новий запит на РЕКЛАМУ"),
        "інше": ("💬", "Нове повідомлення")
    }
    emoji, label = category_labels.get(category, ("📨", "Новий ЗАПИТ"))

    if is_anonymous:
        user_info = f"{emoji} <b>{label} (👻 АНОНІМНО)</b>\n\n"
    else:
        user_info = f"{emoji} <b>{label}</b> від @{username} (ID: {user_id})\n\n"

    if text:
        user_info += text

    admin_kb = None
    if feedback_id and not is_anonymous:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Відповісти", callback_data=f"reply_to_{feedback_id}"),
                InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish_to_{feedback_id}")
            ]
        ])

    successful_sends = 0
    failed_admins = []

    for admin_id in settings.ADMIN_IDS:
        try:
            if photo:
                await bot.send_photo(admin_id, photo[-1].file_id, caption=user_info,
                                   parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            elif document:
                await bot.send_document(admin_id, document.file_id, caption=user_info,
                                      parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            elif video:
                await bot.send_video(admin_id, video.file_id, caption=user_info,
                                   parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            else:
                await bot.send_message(admin_id, user_info, reply_markup=admin_kb,
                                     parse_mode=ParseMode.HTML)
            successful_sends += 1
            logger.info(f"✅ Повідомлення надіслано адміну {admin_id}")
        except Exception as e:
            error_msg = str(e)
            if "chat not found" in error_msg or "Forbidden" in error_msg:
                logger.warning(f"⚠️ Адмін {admin_id} не запустив бота! Попросіть його натиснути /start")
                failed_admins.append(admin_id)
            else:
                logger.error(f"⚠️ Помилка надсилання адміну {admin_id}: {e}")
                failed_admins.append(admin_id)

    if successful_sends > 0:
        logger.info(f"📨 Повідомлення доставлено {successful_sends}/{len(settings.ADMIN_IDS)} адмінам")

    if failed_admins:
        logger.warning(f"❌ Не доставлено адмінам: {failed_admins}")
        logger.warning("💡 Переконайтесь, що всі адміни запустили бота командою /start")
