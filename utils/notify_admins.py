# utils/notify_admins.py
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
):
    """Надсилає повідомлення всім адмінам + в лог-групу"""
    username = username or "Без юзернейму"

    if is_anonymous:
        user_info = f"Новий {category} 👻 (анонімно)\n\n"
    else:
        user_info = f"Новий {category} від @{username} (ID: {user_id})\n\n"

    if text:
        user_info += text

    # Клавіатура для адмінів з кнопкою "Ответити"
    reply_kb = None
    if feedback_id and not is_anonymous:
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответити", callback_data=f"reply_to_{feedback_id}")]
        ])

    # Надсилаємо кожному адміну
    for admin_id in settings.ADMIN_IDS:
        try:
            if photo:
                await bot.send_photo(admin_id, photo[-1].file_id, caption=user_info, reply_markup=reply_kb)
            elif document:
                await bot.send_document(admin_id, document.file_id, caption=user_info, reply_markup=reply_kb)
            elif video:
                await bot.send_video(admin_id, video.file_id, caption=user_info, reply_markup=reply_kb)
            else:
                await bot.send_message(admin_id, user_info, reply_markup=reply_kb)
        except Exception as e:
            print(f"Не вдалося надіслати адміну {admin_id}: {e}")

    # Надсилаємо в загальну групу логів (без кнопки)
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
        print(f"Не вдалося надіслати в групу логів: {e}")
