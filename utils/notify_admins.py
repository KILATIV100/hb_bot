# utils/notify_admins.py
import html  # <--- Додали імпорт
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from config import settings

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
    username = username or "Без юзернейму"
    clean_category = category.strip().lower() if category else "інше"

    category_labels = {
        "новина": ("📰", "Нова НОВИНА"),
        "реклама": ("📢", "Новий запит на РЕКЛАМУ"),
        "інше": ("💬", "Нове повідомлення")
    }
    emoji, label = category_labels.get(clean_category, ("📨", "Новий ЗАПИТ"))

    # 🔥 ЕКРАНУВАННЯ ДАНИХ (Захист від ін'єкцій)
    safe_username = html.quote(username)
    safe_text = html.quote(text) if text else None

    if is_anonymous:
        user_info = f"{emoji} <b>{label} (👻 АНОНІМНО)</b>\n\n"
    else:
        user_info = f"{emoji} <b>{label}</b> від @{safe_username} (ID: {user_id})\n\n"

    if safe_text:
        user_info += safe_text

    # ... далі код без змін ...
    admin_kb = None
    if feedback_id and not is_anonymous:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Відповісти", callback_data=f"reply_to_{feedback_id}"),
                InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish_to_{feedback_id}")
            ]
        ])

    for admin_id in settings.ADMIN_IDS:
        try:
            if photo:
                photo_obj = photo[-1].file_id if isinstance(photo, list) else photo
                await bot.send_photo(admin_id, photo_obj, caption=user_info, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            elif document:
                doc_obj = document.file_id if hasattr(document, 'file_id') else document
                await bot.send_document(admin_id, doc_obj, caption=user_info, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            elif video:
                vid_obj = video.file_id if hasattr(video, 'file_id') else video
                await bot.send_video(admin_id, vid_obj, caption=user_info, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            else:
                await bot.send_message(admin_id, user_info, reply_markup=admin_kb, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Не вдалося надіслати адміну {admin_id}: {e}")
