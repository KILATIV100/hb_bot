# utils/watermark.py
import io
import os
from PIL import Image
from aiogram import Bot
from config import settings

# Шляхи до файлів
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGO_SVG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.svg")
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")


def convert_svg_to_png():
    """Конвертує SVG логотип в PNG (один раз при першому запуску)"""
    try:
        # Перевіряємо, чи існує SVG і чи він не порожній
        if not os.path.exists(LOGO_SVG_PATH) or os.path.getsize(LOGO_SVG_PATH) == 0:
            print(f"⚠️ УВАГА: Файл логотипу {LOGO_SVG_PATH} відсутній або порожній! Вотермарка не працюватиме.")
            return

        if os.path.exists(LOGO_PNG_PATH) and os.path.getsize(LOGO_PNG_PATH) > 0:
            return

        print("🔄 Конвертація SVG в PNG...")
        import cairosvg
        cairosvg.svg2png(
            url=LOGO_SVG_PATH,
            write_to=LOGO_PNG_PATH,
            output_width=150,
            output_height=150
        )
        print("✅ Конвертація успішна.")
    except Exception as e:
        print(f"❌ Помилка при конвертації SVG: {e}")


def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає логотип XBrovary на зображення"""
    try:
        # Спробуємо конвертувати, якщо PNG ще немає
        convert_svg_to_png()

        if not os.path.exists(LOGO_PNG_PATH) or os.path.getsize(LOGO_PNG_PATH) == 0:
            print("⚠️ PNG логотип не знайдено, повертаємо оригінал.")
            return image

        # Завантажуємо логотип
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")

        # Масштабуємо логотип на 40% ширини фото
        logo_width = int(image.width * 0.40)
        if logo_width <= 0: logo_width = 50 # Захист від дуже малих зображень
        
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Налаштування прозорості
        # 0.3 = 30% видимості (дуже блідий)
        # 0.7 = 70% видимості (30% прозорості) - краще видно
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

        # Накладаємо логотип (використовуємо logo як маску для прозорості)
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
        
        # Конвертуємо назад в RGB для JPEG (PNG залишає альфа-канал і може бути важким)
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
        print(f"❌ Критична помилка у add_watermark_and_send: {e}")
        # Якщо щось пішло не так, публікуємо оригінал
        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=file_id,
            caption=caption,
            parse_mode=parse_mode
        )
