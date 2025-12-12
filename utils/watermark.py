# utils/watermark.py
import io
import os
import asyncio
from math import ceil
from PIL import Image, ImageEnhance

# Хак для совместимости версий Pillow
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

def create_tiled_watermark(base_width: int, base_height: int) -> Image.Image:
    """
    Создает прозрачное изображение размером с base_width x base_height,
    полностью заполненное паттерном из логотипов.
    """
    if not os.path.exists(LOGO_PNG_PATH):
        # Если лого нет, возвращаем пустой прозрачный слой
        return Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))

    # 1. Загружаем и готовим логотип
    logo = Image.open(LOGO_PNG_PATH).convert("RGBA")
    
    # Размер логотипа = 15% от ширины основного изображения (аккуратный размер)
    target_logo_width = int(base_width * 0.15)
    if target_logo_width < 50: target_logo_width = 50  # Минимальный размер
    
    aspect_ratio = logo.height / logo.width
    target_logo_height = int(target_logo_width * aspect_ratio)
    
    logo = logo.resize((target_logo_width, target_logo_height), Image.Resampling.LANCZOS)

    # 2. Поворачиваем логотип (-30 градусов)
    logo = logo.rotate(30, expand=True, resample=Image.Resampling.BICUBIC)

    # 3. Делаем полупрозрачным (15% непрозрачности)
    alpha = logo.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(0.15) # 0.15 = 15% видимости
    logo.putalpha(alpha)

    # 4. Создаем пустой слой для паттерна
    watermark_layer = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
    
    # 5. Заполняем плиткой
    logo_w, logo_h = logo.size
    
    # Шаг сетки (расстояние между логотипами)
    step_x = int(logo_w * 1.5)
    step_y = int(logo_h * 1.5)

    for y in range(0, base_height, step_y):
        for x in range(0, base_width, step_x):
            # Смещаем каждый второй ряд для "шахматного" эффекта
            offset_x = int(step_x / 2) if (y // step_y) % 2 == 1 else 0
            
            draw_x = x + offset_x
            
            # Если вылезли за край, не рисуем лишнее (оптимизация не критична здесь)
            if draw_x < base_width - logo_w * 0.2: 
                watermark_layer.paste(logo, (draw_x, y), logo)

    return watermark_layer

def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладывает паттерн на фото"""
    try:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
            
        # Генерируем слой с паттерном под размер фото
        pattern = create_tiled_watermark(image.width, image.height)
        
        # Накладываем (композитинг)
        return Image.alpha_composite(image, pattern)
        
    except Exception as e:
        print(f"Error overlay: {e}")
        return image

def process_video_sync(input_path: str, output_path: str):
    """Синхронна обробка відео через MoviePy з паттерном"""
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    video = None
    final = None
    
    try:
        video = VideoFileClip(input_path)
        
        # 1. Генерируем паттерн как картинку PIL
        # Важливо: MoviePy очікує numpy array або шлях. Збережемо тимчасово.
        w, h = video.size
        pattern_img = create_tiled_watermark(w, h)
        
        pattern_path = output_path + "_pattern.png"
        pattern_img.save(pattern_path, format="PNG")
        
        # 2. Создаем ImageClip из паттерна на всю длину видео
        watermark_clip = (ImageClip(pattern_path)
                          .set_duration(video.duration)
                          .set_position(("center", "center"))) # Паттерн и так во весь экран
        
        # 3. Накладываем
        final = CompositeVideoClip([video, watermark_clip])

        # 4. Рендерим
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4, logger=None)
        
        # Удаляем временный файл паттерна
        if os.path.exists(pattern_path):
            os.remove(pattern_path)
            
    except Exception as e:
        print(f"MoviePy error: {e}")
        raise e
    finally:
        try:
            if final: final.close()
            if video: video.close()
        except: pass

async def process_media_for_album(bot: Bot, file_id: str, file_type: str, use_watermark: bool = True):
    """
    Готує об'єкт InputMedia для альбому (з вотермаркою або без).
    """
    try:
        if file_type == 'photo':
            if use_watermark:
                file = await bot.get_file(file_id)
                file_data = await bot.download_file(file.file_path)
                image = Image.open(io.BytesIO(file_data.read()))
                
                # Накладываем паттерн
                processed_img = overlay_logo_on_image(image)
                
                output = io.BytesIO()
                # Конвертируем в RGB для JPEG (убираем альфа-канал)
                if processed_img.mode == "RGBA":
                    background = Image.new("RGB", processed_img.size, (255, 255, 255))
                    background.paste(processed_img, mask=processed_img.split()[3]) # 3 is the alpha channel
                    processed_img = background
                
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
                    
                    # Запускаем обработку видео
                    await asyncio.to_thread(process_video_sync, input_path, output_path)
                    
                    video_file = FSInputFile(output_path)
                    return InputMediaVideo(media=video_file)
            else:
                return InputMediaVideo(media=file_id)
        
        # Fallback для документов и прочего
        return InputMediaPhoto(media=file_id)
                
    except Exception as e:
        print(f"❌ Error processing media {file_id}: {e}")
        if file_type == 'photo': return InputMediaPhoto(media=file_id)
        return InputMediaVideo(media=file_id)
