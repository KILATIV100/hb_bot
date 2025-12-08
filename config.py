from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: List[int]
    FEEDBACK_CHAT_ID: int   # обов'язково вказуємо тип int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
