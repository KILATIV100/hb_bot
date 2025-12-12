import io
import os
import asyncio
import logging
from PIL import Image, ImageEnhance

# Налаштування логування помилок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хак для сумісності версій Pillow
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto, InputMediaVideo, FSInputFile
from config import settings

# Семафор, щоб не спалити процесор обробкою відео
video_processing_semaphore = asyncio.Semaphore(1)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def create_tiled_watermark(base_width: int, base_height: int) -> Image.Image:
    """Створює шар з патерном (водяний знак плиткою)"""
    try:
        if not os.path.exists(LOGO_PNG_PATH):
            logger.warning(f"Logo not found at {LOGO_PNG_PATH}")
            return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

        # Відкриваємо лого
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")
        
        # Розмір лого = 15% від ширини фото (але не менше 50px)
        target_w = max(50, int(base_width * 0.15))
        ratio = logo.height / logo.width
        target_h = int(target_w * ratio)
        
        logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Поворот -30 градусів
        logo = logo.rotate(30, expand=True, resample=Image.Resampling.BICUBIC)

        # Прозорість 15%
        # Створюємо нове зображення для зміни альфа-каналу, щоб уникнути помилок з read-only
        r, g, b, alpha = logo.split()
        alpha = ImageEnhance.Brightness(alpha).enhance(0.15)
        logo.putalpha(alpha)

        # Створюємо пустий шар
        layer = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        logo_w, logo_h = logo.size

        # Крок сітки
        step_x = int(logo_w * 1.5)
        step_y = int(logo_h * 1.5)

        # Заповнюємо
        for y in range(0, base_height, step_y):
            for x in range(0, base_width, step_x):
                # Зміщення кожного другого ряду
                offset = int(step_x / 2) if (y // step_y) % 2 == 1 else 0
                draw_x = x + offset
                
                # Малюємо тільки якщо в межах зображення (з невеликим запасом)
                if draw_x < base_width:
                    layer.paste(logo, (draw_x, y), logo)
        
        return layer
    except Exception as e:
        logger.error(f"Error creating tile pattern: {e}")
        return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає патерн на фото"""
    try:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        pattern = create_tiled_watermark(image.width, image.height)
        return Image.alpha_composite(image, pattern)
    except Exception as e:
        logger.error(f"Error overlaying logo: {e}")
        return image

def process_video_sync(input_path: str, output_path: str):
    """Обробка відео через MoviePy"""
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    except ImportError:
        logger.error("MoviePy not installed or ffmpeg missing!")
        return

    video = None
    final = None
    pattern_path = output_path + "_pattern.png"

    try:
        video = VideoFileClip(input_path)
        
        # Генеруємо картинку патерну
        w, h = video.size
        pattern_img = create_tiled_watermark(w, h)
        pattern_img.save(pattern_path, format="PNG")
        
        # Накладаємо на відео
        watermark_clip = (ImageClip(pattern_path)
                          .set_duration(video.duration)
                          .set_position(("center", "center")))
        
        final = CompositeVideoClip([video, watermark_clip])
        
        # Рендер
        final.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast",   # Швидше, але файл трохи більший
            threads=4, 
            logger=None           # Прибрати шум у консолі
        )
        
    except Exception as e:
        logger.error(f"MoviePy failed: {e}")
        raise e # Прокидаємо помилку, щоб відправити оригінал
    finally:
        # Чистимо ресурси
        try:
            if os.path.exists(pattern_path): os.remove(pattern_path)
            if final: final.close()
            if video: video.close()
        except: pass

async def process_media_for_album(bot: Bot, file_id: str, file_type: str, use_watermark: bool = True):
    """
    Готує медіа. Якщо помилка — повертає оригінал.
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
                # Конвертуємо в RGB (JPEG не любить прозорість)
                if processed_img.mode == "RGBA":
                    background = Image.new("RGB", processed_img.size, (255, 255, 255))
                    background.paste(processed_img, mask=processed_img.split()[3])
                    processed_img = background
                elif processed_img.mode != "RGB":
                    processed_img = processed_img.convert("RGB")
                
                processed_img.save(output, format="JPEG", quality=90)
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
                    
                    try:
                        # Запускаємо важку обробку в окремому потоці
                        await asyncio.to_thread(process_video_sync, input_path, output_path)
                        
                        if os.path.exists(output_path):
                            return InputMediaVideo(media=FSInputFile(output_path))
                        else:
                            # Якщо файл не створився — повертаємо оригінал
                            logger.error("Video output file not created, sending original")
                            return InputMediaVideo(media=file_id)
                    except Exception as e:
                        logger.error(f"Video processing failed: {e}")
                        return InputMediaVideo(media=file_id)
            else:
                return InputMediaVideo(media=file_id)
        
        # Якщо документ
        return InputMediaPhoto(media=file_id)

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in process_media_for_album: {e}")
        # План Б: повертаємо ID файлу, щоб хоч щось відправилось
        if file_type == 'video': return InputMediaVideo(media=file_id)
        return InputMediaPhoto(media=file_id)
