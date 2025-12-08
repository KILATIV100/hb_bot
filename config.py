# config.py (без змін, але DB_URL з env)
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = [7363233852]  # твої ID, через кому в []
    FEEDBACK_CHAT_ID: int = +AzCLSC9rTz5lOTQy  # чат для логів (заміни на реальний з групи)
    DATABASE_URL: str # з Railway

    class Config:
        env_file = ".env"

settings = Settings()
