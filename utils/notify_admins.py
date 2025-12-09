# utils/notify_admins.py
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
) -> int | None:
    """Надсилає повідомлення всім адмінам + в лог-групу з кнопками
    Повертає message_id з групи логів для подальших reply"""
    username = username or "Без юзернейму"

    # Категорія з емодзі
    category_emoji = {
        "новина": "📰",
        "реклама": "📢",
        "інше": "💬"
    }
    emoji = category_emoji.get(category, "📨")

    if is_anonymous:
        user_info = f"{emoji} <b>Новий {category.upper()} (👻 АНОНІМНО)</b>\n\n"
    else:
        user_info = f"{emoji} <b>Новий {category.upper()}</b> від @{username} (ID: {user_id})\n\n"

    if text:
        user_info += text

    # Клавіатура ДЛЯ ГРУПИ ЛОГІВ з двома кнопками
    group_kb = None
    if feedback_id and not is_anonymous:
        group_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Відповісти", callback_data=f"reply_to_{feedback_id}"),
                InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish_to_{feedback_id}")
            ]
        ])

    # Надсилаємо кожному адміну БЕЗ КНОПОК (приватні чати)
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
            print(f"Не вдалося надіслати адміну {admin_id}: {e}")

    # Надсилаємо в групу логів З КНОПКАМИ та повертаємо message_id
    group_message_id = None
    try:
        if photo:
            msg = await bot.send_photo(settings.FEEDBACK_CHAT_ID, photo[-1].file_id, caption=user_info,
                               parse_mode=ParseMode.HTML, reply_markup=group_kb)
        elif document:
            msg = await bot.send_document(settings.FEEDBACK_CHAT_ID, document.file_id, caption=user_info,
                                  parse_mode=ParseMode.HTML, reply_markup=group_kb)
        elif video:
            msg = await bot.send_video(settings.FEEDBACK_CHAT_ID, video.file_id, caption=user_info,
                               parse_mode=ParseMode.HTML, reply_markup=group_kb)
        else:
            msg = await bot.send_message(settings.FEEDBACK_CHAT_ID, user_info, reply_markup=group_kb)
        group_message_id = msg.message_id
    except Exception as e:
        print(f"Не вдалося надіслати в групу логів: {e}")

    return group_message_id
