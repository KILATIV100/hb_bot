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
    """Створює шар-паттерн (сітку). Логотип 100% непрозорий."""
    try:
        if not os.path.exists(LOGO_PNG_PATH):
            logger.warning(f"Logo not found: {LOGO_PNG_PATH}")
            return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")
        
        # --- НАЛАШТУВАННЯ ---
        # 1. Розмір: 40% від ширини фото
        target_w = int(base_width * 0.40)
        if target_w < 50: target_w = 50
        
        ratio = logo.height / logo.width
        target_h = int(target_w * ratio)
        
        logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # 2. Прозорість: МИ ПРИБРАЛИ ЗМЕНШЕННЯ ПРОЗОРОСТІ.
        # Логотип залишається таким, яким він є в оригіналі.
        # ---------------------

        # Створюємо пустий прозорий шар
        layer = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        logo_w, logo_h = logo.size

        # Відступ між логотипами (лого + 5% простору)
        step_x = int(logo_w * 1.05)
        step_y = int(logo_h * 1.05)

        # Заповнюємо шар (Паттерн)
        start_x = -int(logo_w * 0.2)
        start_y = -int(logo_h * 0.2)

        for y in range(start_y, base_height, step_y):
            for x in range(start_x, base_width, step_x):
                layer.paste(logo, (x, y), logo)
        
        return layer

    except Exception as e:
        logger.error(f"Error creating pattern: {e}")
        return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає патерн на фото"""
    try:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        pattern = create_pattern_layer(image.width, image.height)
        return Image.alpha_composite(image, pattern)
    except Exception as e:
        logger.error(f"Error overlaying logo: {e}")
        return image

def process_video_sync(input_path: str, output_path: str):
    """Обробка відео через MoviePy"""
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
        
        # Генеруємо картинку патерну
        w, h = video.size
        pattern_img = create_pattern_layer(w, h)
        pattern_img.save(pattern_file, format="PNG")
        
        # Накладаємо на відео
        watermark_clip = (ImageClip(pattern_file)
                          .set_duration(video.duration)
                          .set_position(("center", "center")))
        
        final = CompositeVideoClip([video, watermark_clip])

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
    try:
        # --- ФОТО ---
        if file_type == 'photo':
            if use_watermark:
                file = await bot.get_file(file_id)
                file_data = await bot.download_file(file.file_path)
                image = Image.open(io.BytesIO(file_data.read()))
                
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

        # --- ВІДЕО ---
        elif file_type == 'video':
            if use_watermark:
                async with video_processing_semaphore:
                    input_path = os.path.join(TEMP_DIR, f"{file_id}_in.mp4")
                    output_path = os.path.join(TEMP_DIR, f"{file_id}_out.mp4")
                    
                    file = await bot.get_file(file_id)
                    await bot.download_file(file.file_path, destination=input_path)
                    
                    try:
                        await asyncio.to_thread(process_video_sync, input_path, output_path)
                        
                        if os.path.exists(output_path):
                            return InputMediaVideo(media=FSInputFile(output_path))
                    except Exception as e:
                        logger.error(f"Video failed: {e}")
                    
                    return InputMediaVideo(media=file_id)
            else:
                return InputMediaVideo(media=file_id)
        
        return InputMediaPhoto(media=file_id)

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in process_media_for_album: {e}")
        if file_type == 'video': return InputMediaVideo(media=file_id)
        return InputMediaPhoto(media=file_id)
