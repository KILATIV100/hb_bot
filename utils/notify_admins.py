# utils/notify_admins.py
import html
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.enums import ParseMode
from config import settings


async def notify_admins(
    bot: Bot,
    user_id: int,
    username: str,
    category: str,
    feedback_id: int | None = None,
    text: str | None = None,
    media_files: list | None = None,  # 🔥 ЦЕЙ АРГУМЕНТ ОБОВ'ЯЗКОВИЙ
    is_anonymous: bool = False,
) -> None:
    """
    Надсилає повідомлення адмінам.
    Якщо медіа одне - кнопки кріпляться до нього.
    Якщо це альбом - спочатку йде альбом, потім текст із кнопками.
    """
    username = username or "Без юзернейму"
    clean_category = category.strip().lower() if category else "інше"

    category_labels = {
        "новина": ("📰", "Нова НОВИНА"),
        "реклама": ("📢", "Новий запит на РЕКЛАМУ"),
        "інше": ("💬", "Нове повідомлення")
    }
    emoji, label = category_labels.get(clean_category, ("📨", "Новий ЗАПИТ"))

    safe_username = html.escape(username)
    safe_text = html.escape(text) if text else "Без тексту"

    # Формуємо заголовок
    if is_anonymous:
        header = f"{emoji} <b>{label} (👻 АНОНІМНО)</b>\n"
    else:
        header = f"{emoji} <b>{label}</b> від @{safe_username} (ID: {user_id})\n"
    
    full_text = f"{header}\n📝 {safe_text}"

    # Клавіатура
    admin_kb = None
    if feedback_id and not is_anonymous:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Відповісти", callback_data=f"reply_to_{feedback_id}"),
                InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish_to_{feedback_id}")
            ]
        ])

    # Розсилка кожному адміну
    for admin_id in settings.ADMIN_IDS:
        try:
            # Сценарій 1: Немає медіа (тільки текст)
            if not media_files:
                await bot.send_message(admin_id, full_text, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
                continue

            # Сценарій 2: Один файл (Фото/Відео/Документ)
            if len(media_files) == 1:
                file_data = media_files[0]
                file_id = file_data['file_id']
                file_type = file_data['type']

                if file_type == 'photo':
                    await bot.send_photo(admin_id, file_id, caption=full_text, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
                elif file_type == 'video':
                    await bot.send_video(admin_id, file_id, caption=full_text, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
                elif file_type == 'document':
                    await bot.send_document(admin_id, file_id, caption=full_text, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
                continue

            # Сценарій 3: АЛЬБОМ (> 1 файлу)
            # 1. Формуємо медіа-групу
            media_group = []
            for m in media_files:
                if m['type'] == 'photo':
                    media_group.append(InputMediaPhoto(media=m['file_id']))
                elif m['type'] == 'video':
                    media_group.append(InputMediaVideo(media=m['file_id']))
            
            if media_group:
                # Відправляємо альбом (без кнопок)
                await bot.send_media_group(admin_id, media=media_group)
            
            # 2. Відправляємо окреме повідомлення з текстом і кнопками
            control_msg = f"{header}\n⚠️ <b>Отримано альбом ({len(media_files)} файлів).</b>\nТекст новини:\n\n{safe_text}"
            await bot.send_message(admin_id, control_msg, parse_mode=ParseMode.HTML, reply_markup=admin_kb)

        except Exception as e:
            print(f"❌ Не вдалося надіслати адміну {admin_id}: {e}")
