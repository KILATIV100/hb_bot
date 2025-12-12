# utils/watermark.py
import io
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot
from config import settings


async def add_watermark_and_send(
    bot: Bot,
    file_id: str,
    caption: str,
    parse_mode: str = "HTML"
) -> None:
    """
    Завантажує файл, додає водяний знак "#нампишуть" і публікує на канал
    """
    try:
        # Завантажуємо файл з Telegram
        file = await bot.get_file(file_id)
        file_data = await bot.download_file(file.file_path)

        # Відкриваємо зображення
        image = Image.open(io.BytesIO(file_data.read()))

        # Додаємо водяний знак
        draw = ImageDraw.Draw(image)

        # Розміри тексту
        watermark_text = "#нампишуть"
        text_color = (255, 255, 255, 200)  # Білий з прозорістю

        # Намагаємося завантажити шрифт, якщо не буде - використовуємо дефолтний
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()

        # Визначаємо позицію (нижній правий кут з відступом)
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        position = (image.width - text_width - 20, image.height - text_height - 20)

        # Додаємо тень для кращої видимості
        shadow_color = (0, 0, 0, 150)
        draw.text((position[0] + 2, position[1] + 2), watermark_text, font=font, fill=shadow_color)

        # Додаємо основний текст
        draw.text(position, watermark_text, font=font, fill=text_color)

        # Зберігаємо в BytesIO
        watermarked = io.BytesIO()
        image.save(watermarked, format="JPEG", quality=95)
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
