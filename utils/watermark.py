# utils/watermark.py
import io
import os
from PIL import Image
from aiogram import Bot
from aiogram.types import BufferedInputFile
from config import settings

# Шляхи до файлів
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")


def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає логотип XBrovary на зображення"""
    try:
        # Перевіряємо наявність PNG
        if not os.path.exists(LOGO_PNG_PATH):
            print(f"⚠️ Файл логотипу {LOGO_PNG_PATH} відсутній. Публікуємо без вотермарки.")
            return image

        # Завантажуємо логотип
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")

        # Масштабуємо логотип на 40% ширини фото
        logo_width = int(image.width * 0.40)
        # Захист від занадто малих зображень
        if logo_width <= 0: logo_width = 50
        
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Налаштування прозорості
        # 0.7 = 70% видимості (30% прозорості)
        if logo.mode == "RGBA":
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.7)) 
            logo.putalpha(alpha)

        # Конвертуємо основне зображення в RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Визначаємо позицію (центр)
        x = (image.width - logo_width) // 2
        y = (image.height - logo_height) // 2

        # Накладаємо логотип
        image.paste(logo, (x, y), logo)

        return image
    except Exception as e:
        print(f"❌ Помилка при накладанні логотипу: {e}")
        return image


async def add_watermark_and_send(
    bot: Bot,
    file_id: str,
    caption: str,
    parse_mode: str = "HTML"
) -> None:
    """
    Завантажує файл, додає логотип і публікує
    """
    try:
        # Завантажуємо файл з Telegram
        file = await bot.get_file(file_id)
        file_data = await bot.download_file(file.file_path)

        # Відкриваємо зображення
        image = Image.open(io.BytesIO(file_data.read()))

        # Накладаємо логотип
        image_with_logo = overlay_logo_on_image(image)

        # Зберігаємо результат в BytesIO
        watermarked = io.BytesIO()
        
        # Конвертуємо назад в RGB для JPEG (PNG не підходить для send_photo як основний формат фото)
        if image_with_logo.mode == "RGBA":
            image_with_logo = image_with_logo.convert("RGB")
            
        image_with_logo.save(watermarked, format="JPEG", quality=95)
        watermarked.seek(0)

        # 🔥 Створюємо об'єкт файлу для aiogram 3
        photo_file = BufferedInputFile(watermarked.getvalue(), filename="watermarked_image.jpg")

        # Публікуємо на канал
        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=photo_file,
            caption=caption,
            parse_mode=parse_mode
        )

    except Exception as e:
        print(f"❌ Помилка при додаванні водяного знаку: {e}")
        # Якщо щось пішло не так, просто публікуємо без водяного знака
        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=file_id,
            caption=caption,
            parse_mode=parse_mode
        )
