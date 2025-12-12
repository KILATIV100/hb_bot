# utils/watermark.py
import io
import os
import asyncio
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto, InputMediaVideo, FSInputFile
from config import settings

# Семафор для обмеження навантаження при обробці відео
video_processing_semaphore = asyncio.Semaphore(1)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# Шлях до логотипу (використовуємо PNG, бо він надійніший)
LOGO_PNG_PATH = os.path.join(BASE_DIR, "assets", "xbrovary_logo.png")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def overlay_logo_on_image(image: Image.Image) -> Image.Image:
    """Накладає логотип 5 разів (центр + кути)"""
    try:
        if not os.path.exists(LOGO_PNG_PATH): return image
        logo = Image.open(LOGO_PNG_PATH).convert("RGBA")
        
        # Масштабуємо лого
        logo_width = int(image.width * 0.40)
        if logo_width <= 0: logo_width = 50
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Прозорість
        if logo.mode == "RGBA":
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.7)) 
            logo.putalpha(alpha)

        if image.mode != "RGBA": image = image.convert("RGBA")

        W, H = image.width, image.height
        w, h = logo_width, logo_height
        padding = int(W * 0.05)

        # Позиції: центр + 4 кути
        positions = [
            ((W - w) // 2, (H - h) // 2),
            (padding, padding),
            (W - w - padding, padding),
            (padding, H - h - padding),
            (W - w - padding, H - h - padding)
        ]

        for x, y in positions:
            image.paste(logo, (x, y), logo)
        return image
    except Exception as e:
        print(f"Error overlay: {e}")
        return image

def process_video_sync(input_path: str, output_path: str, logo_path: str):
    """Синхронна обробка відео через MoviePy"""
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    video = None
    final = None
    try:
        video = VideoFileClip(input_path)
        if os.path.exists(logo_path):
            base_logo = (ImageClip(logo_path).set_duration(video.duration)
                         .resize(width=video.w * 0.40).set_opacity(0.7))
            W, H = video.size
            w, h = base_logo.size
            padding = int(W * 0.05)
            
            logos = [
                base_logo.set_position(("center", "center")),
                base_logo.set_position((padding, padding)),
                base_logo.set_position((W - w - padding, padding)),
                base_logo.set_position((padding, H - h - padding)),
                base_logo.set_position((W - w - padding, H - h - padding))
            ]
            final = CompositeVideoClip([video, *logos])
        else:
            final = video

        final.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4, logger=None)
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
    Це та сама функція, яку шукає admin.py!
    """
    try:
        if file_type == 'photo':
            if use_watermark:
                file = await bot.get_file(file_id)
                file_data = await bot.download_file(file.file_path)
                image = Image.open(io.BytesIO(file_data.read()))
                
                processed_img = overlay_logo_on_image(image)
                
                output = io.BytesIO()
                if processed_img.mode == "RGBA": processed_img = processed_img.convert("RGB")
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
                        await asyncio.to_thread(process_video_sync, input_path, output_path, LOGO_PNG_PATH)
                        video_file = FSInputFile(output_path)
                        return InputMediaVideo(media=video_file)
                    else:
                        return InputMediaVideo(media=file_id)
            else:
                return InputMediaVideo(media=file_id)
        
        # Якщо тип невідомий або документ
        return InputMediaPhoto(media=file_id)
                
    except Exception as e:
        print(f"❌ Error processing media {file_id}: {e}")
        if file_type == 'photo': return InputMediaPhoto(media=file_id)
        return InputMediaVideo(media=file_id)
