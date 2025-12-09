from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: List[int]
    FEEDBACK_CHAT_ID: int   # Група для логів повідомлень
    CHANNEL_ID: int  # Основний канал для публікацій

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
