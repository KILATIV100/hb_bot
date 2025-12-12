# utils/watermark.py
import io
import os
from PIL import Image
from aiogram import Bot
from aiogram.types import BufferedInputFile
from config import settings

# Шляхи до файлів
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGO_SVG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.svg")
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")


def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає логотип XBrovary на зображення"""
    try:
        # Перевіряємо наявність PNG (пріоритет)
        if not os.path.exists(LOGO_PNG_PATH) or os.path.getsize(LOGO_PNG_PATH) == 0:
            # Спроба конвертації (тільки якщо є бібліотеки), інакше ігноруємо
            try:
                import cairosvg
                if os.path.exists(LOGO_SVG_PATH) and os.path.getsize(LOGO_SVG_PATH) > 0:
                    print("🔄 Спроба конвертації SVG в PNG...")
                    cairosvg.svg2png(url=LOGO_SVG_PATH, write_to=LOGO_PNG_PATH, output_width=150, output_height=150)
            except Exception:
                print("⚠️ Бібліотека cairosvg не працює або відсутня. Вотермарка можлива тільки з готовим PNG.")
        
        # Ще раз перевіряємо PNG після спроби конвертації
        if not os.path.exists(LOGO_PNG_PATH) or os.path.getsize(LOGO_PNG_PATH) == 0:
            print("⚠️ Файл xbrovary_logo.png відсутній. Публікуємо без вотермарки.")
            return image

        # Завантажуємо логотип
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")

        # Масштабуємо логотип на 40% ширини фото
        logo_width = int(image.width * 0.40)
        if logo_width <= 0: logo_width = 50
        
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Прозорість 30% (альфа = 0.7)
        if logo.mode == "RGBA":
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.7)) 
            logo.putalpha(alpha)

        # Конвертуємо основне зображення в RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Центруємо
        x = (image.width - logo_width) // 2
        y = (image.height - logo_height) // 2

        # Накладаємо
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
    Завантажує файл, додає логотип і публікує (ВИПРАВЛЕНО помилку Pydantic)
    """
    try:
        # Завантажуємо файл
        file = await bot.get_file(file_id)
        file_data = await bot.download_file(file.file_path)

        # Відкриваємо і обробляємо
        image = Image.open(io.BytesIO(file_data.read()))
        image_with_logo = overlay_logo_on_image(image)

        # Зберігаємо результат в пам'ять
        watermarked = io.BytesIO()
        if image_with_logo.mode == "RGBA":
            image_with_logo = image_with_logo.convert("RGB")
            
        image_with_logo.save(watermarked, format="JPEG", quality=95)
        watermarked.seek(0)

        # 🔥 ВАЖЛИВО: Обгортаємо байти в BufferedInputFile для aiogram 3.x
        photo_file = BufferedInputFile(watermarked.getvalue(), filename="image_with_logo.jpg")

        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=photo_file,
            caption=caption,
            parse_mode=parse_mode
        )

    except Exception as e:
        print(f"❌ Помилка у add_watermark_and_send: {e}")
        # Фолбек: відправляємо оригінал по file_id (це завжди працює)
        await bot.send_photo(
            settings.CHANNEL_ID,
            photo=file_id,
            caption=caption,
            parse_mode=parse_mode
        )
