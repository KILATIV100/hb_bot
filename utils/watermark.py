# utils/watermark.py
import io
import os
from PIL import Image
from aiogram import Bot
from config import settings

# Шлях до SVG логотипу
LOGO_SVG_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "xbrovary_logo.svg")
LOGO_PNG_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "xbrovary_logo.png")


def convert_svg_to_png():
    """Конвертує SVG логотип в PNG (один раз при першому запуску)"""
    try:
        if os.path.exists(LOGO_PNG_PATH):
            return

        import cairosvg
        cairosvg.svg2png(
            url=LOGO_SVG_PATH,
            write_to=LOGO_PNG_PATH,
            output_width=150,
            output_height=150
        )
    except Exception as e:
        print(f"Помилка при конвертації SVG: {e}")


def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає логотип XBrovary на зображення з напівпрозорістю"""
    try:
        # Конвертуємо логотип один раз при запуску
        convert_svg_to_png()

        if not os.path.exists(LOGO_PNG_PATH):
            return image

        # Завантажуємо логотип
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")

        # Масштабуємо логотип залежно від розміру фото
        # Логотип займає ~15% ширини фото
        logo_width = max(80, int(image.width * 0.12))
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Робимо логотип напівпрозорим
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.5))  # 50% прозорість
        logo.putalpha(alpha)

        # Конвертуємо основне зображення в RGBA для накладання
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Визначаємо позицію (центр зображення)
        x = (image.width - logo_width) // 2
        y = (image.height - logo_height) // 2

        # Накладаємо логотип в центрі
        image.paste(logo, (x, y), logo)

        return image
    except Exception as e:
        print(f"Помилка при накладанні логотипу: {e}")
        return image


async def add_watermark_and_send(
    bot: Bot,
    file_id: str,
    caption: str,
    parse_mode: str = "HTML"
) -> None:
    """
    Завантажує файл, додає логотип XBrovary як вотермарку і публікує на канал
    """
    try:
        # Завантажуємо файл з Telegram
        file = await bot.get_file(file_id)
        file_data = await bot.download_file(file.file_path)

        # Відкриваємо зображення
        image = Image.open(io.BytesIO(file_data.read()))

        # Накладаємо логотип
        image_with_logo = overlay_logo_on_image(image)

        # Зберігаємо в BytesIO
        watermarked = io.BytesIO()
        # Конвертуємо назад в RGB для JPEG
        if image_with_logo.mode == "RGBA":
            image_with_logo = image_with_logo.convert("RGB")
        image_with_logo.save(watermarked, format="JPEG", quality=95)
        watermarked.seek(0)

        # Публікуємо на канал
        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=watermarked,
            caption=caption,
            parse_mode=parse_mode
        )

    except Exception as e:
        print(f"Помилка при додаванні водяного знаку: {e}")
        # Якщо щось пішло не так, просто публікуємо без водяного знака
        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=file_id,
            caption=caption,
            parse_mode=parse_mode
        )
