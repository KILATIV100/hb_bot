# utils/watermark.py
import io
import os
import asyncio
from PIL import Image

# 🔥 ФІКС ДЛЯ MOVIEPY + PILLOW 10/11
# MoviePy використовує видалений атрибут ANTIALIAS, повертаємо його назад вручну
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from aiogram import Bot
from aiogram.types import BufferedInputFile, FSInputFile
from config import settings

# Шляхи до файлів
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Створюємо папку temp, якщо немає
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає логотип XBrovary: по центру та 4 кутам"""
    try:
        if not os.path.exists(LOGO_PNG_PATH):
            print(f"⚠️ Файл логотипу {LOGO_PNG_PATH} відсутній. Публікуємо без вотермарки.")
            return image

        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")

        # 1. Налаштування розміру (40% від ширини)
        logo_width = int(image.width * 0.40)
        if logo_width <= 0: logo_width = 50
        
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # 2. Налаштування прозорості (70% видимості)
        if logo.mode == "RGBA":
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.7)) 
            logo.putalpha(alpha)

        # Конвертуємо основне зображення в RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # 3. Розрахунок координат
        W, H = image.width, image.height
        w, h = logo_width, logo_height
        padding = int(W * 0.05)  # Відступ 5% від ширини

        positions = [
            ((W - w) // 2, (H - h) // 2),       # Центр
            (padding, padding),                 # Лівий верхній
            (W - w - padding, padding),         # Правий верхній
            (padding, H - h - padding),         # Лівий нижній
            (W - w - padding, H - h - padding)  # Правий нижній
        ]

        # 4. Накладання 5 логотипів
        for x, y in positions:
            image.paste(logo, (x, y), logo)

        return image
    except Exception as e:
        print(f"❌ Помилка при накладанні логотипу: {e}")
        return image


async def add_watermark_and_send(bot: Bot, file_id: str, caption: str, parse_mode: str = "HTML") -> None:
    """Для фото: Завантажує, додає лого і відправляє"""
    try:
        file = await bot.get_file(file_id)
        file_data = await bot.download_file(file.file_path)
        image = Image.open(io.BytesIO(file_data.read()))
        
        image_with_logo = overlay_logo_on_image(image)
        
        watermarked = io.BytesIO()
        if image_with_logo.mode == "RGBA":
            image_with_logo = image_with_logo.convert("RGB")
        image_with_logo.save(watermarked, format="JPEG", quality=95)
        watermarked.seek(0)
        
        photo_file = BufferedInputFile(watermarked.getvalue(), filename="watermarked.jpg")
        await bot.send_photo(settings.CHANNEL_ID, photo=photo_file, caption=caption, parse_mode=parse_mode)
    except Exception as e:
        print(f"❌ Помилка фото-вотермарки: {e}")
        await bot.send_photo(settings.CHANNEL_ID, photo=file_id, caption=caption, parse_mode=parse_mode)


def process_video_sync(input_path: str, output_path: str, logo_path: str):
    """Синхронна функція для обробки відео через moviepy (5 позицій)"""
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    
    video = None
    final = None
    try:
        video = VideoFileClip(input_path)
        
        if os.path.exists(logo_path):
            # Базовий кліп логотипу
            base_logo = (ImageClip(logo_path)
                    .set_duration(video.duration)
                    .resize(width=video.w * 0.40)  # 40% ширини
                    .set_opacity(0.7))
            
            # Розрахунок координат
            W, H = video.size
            w, h = base_logo.size
            padding = int(W * 0.05) # Відступ 5%

            # Позиції для MoviePy
            # set_position повертає копію кліпу з новою позицією
            logo_center = base_logo.set_position(("center", "center"))
            logo_tl = base_logo.set_position((padding, padding))
            logo_tr = base_logo.set_position((W - w - padding, padding))
            logo_bl = base_logo.set_position((padding, H - h - padding))
            logo_br = base_logo.set_position((W - w - padding, H - h - padding))

            # Компонуємо все разом
            final = CompositeVideoClip([video, logo_center, logo_tl, logo_tr, logo_bl, logo_br])
        else:
            final = video

        # Рендерінг
        final.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=4,
            logger=None
        )
        
    except Exception as e:
        print(f"MoviePy Error: {e}")
        raise e
    finally:
        try:
            if final: final.close()
            if video: video.close()
        except:
            pass


async def add_video_watermark_and_send(bot: Bot, file_id: str, caption: str, parse_mode: str = "HTML") -> None:
    """Для відео: Завантажує, обробляє через moviepy і відправляє"""
    input_path = os.path.join(TEMP_DIR, f"{file_id}_in.mp4")
    output_path = os.path.join(TEMP_DIR, f"{file_id}_out.mp4")

    try:
        # 1. Завантажуємо відео
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=input_path)

        # 2. Перевіряємо наявність логотипу
        if not os.path.exists(LOGO_PNG_PATH):
            print("⚠️ Немає логотипу, відправляємо оригінал")
            await bot.send_video(settings.CHANNEL_ID, video=file_id, caption=caption, parse_mode=parse_mode)
            return

        # 3. Обробляємо відео
        print(f"🎬 Обробка відео {file_id} (5 логотипів)...")
        await asyncio.to_thread(process_video_sync, input_path, output_path, LOGO_PNG_PATH)
        print("✅ Обробка завершена успішно")

        # 4. Відправляємо результат
        if os.path.exists(output_path):
            video_file = FSInputFile(output_path)
            await bot.send_video(settings.CHANNEL_ID, video=video_file, caption=caption, parse_mode=parse_mode)
        else:
            raise Exception("Файл результату не створено")

    except Exception as e:
        print(f"❌ Помилка відео-вотермарки: {e}")
        await bot.send_video(settings.CHANNEL_ID, video=file_id, caption=caption, parse_mode=parse_mode)
    
    finally:
        await asyncio.sleep(1)
        if os.path.exists(input_path):
            try: os.remove(input_path)
            except: pass
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass
