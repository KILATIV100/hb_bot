import io
import os
import asyncio
import logging
from PIL import Image, ImageEnhance

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хак для сумісності версій Pillow
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto, InputMediaVideo, FSInputFile
from config import settings

video_processing_semaphore = asyncio.Semaphore(1)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def create_pattern_layer(base_width: int, base_height: int) -> Image.Image:
    """
    Створює прозорий шар, заповнений логотипами (Паттерн)
    Налаштування: Розмір 40%, Без повороту, Прозорість 0.7
    """
    try:
        if not os.path.exists(LOGO_PNG_PATH):
            logger.warning("Logo file not found!")
            return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

        # 1. Відкриваємо лого
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")
        
        # 2. Розмір: 40% від ширини основи
        target_w = int(base_width * 0.40)
        if target_w < 50: target_w = 50
        
        ratio = logo.height / logo.width
        target_h = int(target_w * ratio)
        
        logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # 3. Без повороту (видалено rotate)

        # 4. Прозорість: 0.7 (як було раніше)
        r, g, b, alpha = logo.split()
        alpha = ImageEnhance.Brightness(alpha).enhance(0.7)
        logo.putalpha(alpha)

        # 5. Створюємо шар для патерну
        layer = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        logo_w, logo_h = logo.size

        # Розраховуємо крок сітки (лого + відступ 5% від ширини фото)
        padding_x = int(base_width * 0.05)
        padding_y = int(base_height * 0.05)
        
        step_x = logo_w + padding_x
        step_y = logo_h + padding_y

        # 6. Заповнюємо сіткою
        # Починаємо трохи вище і лівіше, щоб перекрити все
        for y in range(0, base_height, step_y):
            for x in range(0, base_width, step_x):
                # Без зміщення (рівна сітка), бо логотипи великі
                layer.paste(logo, (x, y), logo)
        
        return layer

    except Exception as e:
        logger.error(f"Error creating pattern: {e}")
        return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає шар патерну на фото"""
    try:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Створюємо патерн під розмір конкретного фото
        pattern = create_pattern_layer(image.width, image.height)
        
        # Накладаємо
        return Image.alpha_composite(image, pattern)

    except Exception as e:
        logger.error(f"Error overlaying logo: {e}")
        return image

def process_video_sync(input_path: str, output_path: str, logo_path: str):
    """Обробка відео: створюємо картинку-патерн і накладаємо на все відео"""
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    except ImportError:
        logger.error("MoviePy/ffmpeg not installed!")
        return

    video = None
    final = None
    pattern_file = output_path + "_pattern.png"
    
    try:
        video = VideoFileClip(input_path)
        
        # 1. Генеруємо статичний патерн розміром з відео
        w, h = video.size
        pattern_img = create_pattern_layer(w, h)
        pattern_img.save(pattern_file, format="PNG")
        
        # 2. Накладаємо як картинку
        watermark_clip = (ImageClip(pattern_file)
                          .set_duration(video.duration)
                          .set_position(("center", "center")))
        
        final = CompositeVideoClip([video, watermark_clip])

        # 3. Рендер
        final.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=4, 
            logger=None
        )
    except Exception as e:
        logger.error(f"MoviePy error: {e}")
        raise e
    finally:
        try:
            if os.path.exists(pattern_file): os.remove(pattern_file)
            if final: final.close()
            if video: video.close()
        except: pass

async def process_media_for_album(bot: Bot, file_id: str, file_type: str, use_watermark: bool = True):
    """
    Основна функція для admin.py
    """
    try:
        if file_type == 'photo':
            if use_watermark:
                file = await bot.get_file(file_id)
                file_data = await bot.download_file(file.file_path)
                image = Image.open(io.BytesIO(file_data.read()))
                
                # Обробка
                processed_img = overlay_logo_on_image(image)
                
                output = io.BytesIO()
                # Конвертуємо в RGB
                if processed_img.mode == "RGBA":
                    background = Image.new("RGB", processed_img.size, (255, 255, 255))
                    background.paste(processed_img, mask=processed_img.split()[3])
                    processed_img = background
                elif processed_img.mode != "RGB":
                    processed_img = processed_img.convert("RGB")
                
                processed_img.save(output, format="JPEG", quality=95)
                output.seek(0)
                
                return InputMediaPhoto(media=BufferedInputFile(output.getvalue(), filename="img.jpg"))
            else:
                return InputMediaPhoto(media=file_id)

        elif file_type == 'video':
            if use_watermark:
                async with video_processing_semaphore:
                    input_path = os.path.join(TEMP_DIR, f"{file_id}_in.mp4")
                    output_path = os.path.join(TEMP_DIR, f"{file_id}_out.mp4")
                    
                    file = await bot.get_file(file_id)
                    await bot.download_file(file.file_path, destination=input_path)
                    
                    if os.path.exists(LOGO_PNG_PATH):
                        try:
                            await asyncio.to_thread(process_video_sync, input_path, output_path, LOGO_PNG_PATH)
                            if os.path.exists(output_path):
                                return InputMediaVideo(media=FSInputFile(output_path))
                        except Exception as e:
                            logger.error(f"Video processing failed: {e}")
                    
                    # Якщо щось пішло не так — оригінал
                    return InputMediaVideo(media=file_id)
            else:
                return InputMediaVideo(media=file_id)
        
        return InputMediaPhoto(media=file_id)

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in process_media_for_album: {e}")
        if file_type == 'video': return InputMediaVideo(media=file_id)
        return InputMediaPhoto(media=file_id)
