# database/db.py
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
from config import settings

class DB:
    def __init__(self):
        self.dsn = settings.DATABASE_URL

    async def connect(self):
        self.conn = await psycopg.AsyncConnection.connect(self.dsn, row_factory=dict_row)
        await self.create_tables()

    async def create_tables(self):
        async with self.conn.cursor() as cur:
            # Основна таблиця
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    category TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    group_message_id INT
                )
            ''')
            
            # 🔥 НОВА ТАБЛИЦЯ ДЛЯ МЕДІА (АЛЬБОМІВ)
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS feedback_media (
                    id SERIAL PRIMARY KEY,
                    feedback_id INT REFERENCES feedbacks(id) ON DELETE CASCADE,
                    file_id TEXT,
                    file_type TEXT, -- 'photo', 'video', 'document'
                    media_group_id TEXT
                )
            ''')

            # Таблиці лімітів та відповідей
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id BIGINT PRIMARY KEY,
                    last_feedback TIMESTAMP
                )
            ''')
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS replies (
                    id SERIAL PRIMARY KEY,
                    feedback_id INT REFERENCES feedbacks(id) ON DELETE CASCADE,
                    admin_id BIGINT,
                    reply_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await self.conn.commit()

    async def add_feedback(self, user_id: int, username: str, category: str, content: str) -> int:
        """Створює запис про фідбек і повертає його ID"""
        async with self.conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO feedbacks (user_id, username, category, content) VALUES (%s, %s, %s, %s) RETURNING id",
                (user_id, username, category, content)
            )
            feedback_id = (await cur.fetchone())["id"]
            
            # Оновлюємо ліміт
            await cur.execute(
                "INSERT INTO rate_limits (user_id, last_feedback) VALUES (%s, CURRENT_TIMESTAMP) ON CONFLICT (user_id) DO UPDATE SET last_feedback = CURRENT_TIMESTAMP",
                (user_id,)
            )
            await self.conn.commit()
        return feedback_id

    async def add_media(self, feedback_id: int, file_id: str, file_type: str, media_group_id: str | None = None):
        """🔥 Додає файл до фідбеку"""
        async with self.conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO feedback_media (feedback_id, file_id, file_type, media_group_id) VALUES (%s, %s, %s, %s)",
                (feedback_id, file_id, file_type, media_group_id)
            )
            await self.conn.commit()

    async def get_feedback_media(self, feedback_id: int) -> list:
        """🔥 Отримує всі файли для конкретного фідбеку"""
        async with self.conn.cursor() as cur:
            await cur.execute("SELECT * FROM feedback_media WHERE feedback_id = %s ORDER BY id ASC", (feedback_id,))
            return await cur.fetchall()

    async def check_rate_limit(self, user_id: int) -> bool:
        async with self.conn.cursor() as cur:
            await cur.execute("SELECT last_feedback FROM rate_limits WHERE user_id = %s", (user_id,))
            row = await cur.fetchone()
            if row and (datetime.utcnow() - row["last_feedback"]).total_seconds() < 60:
                return False
        return True

    async def get_stats(self, period: str) -> list:
        async with self.conn.cursor() as cur:
            if period == 'day':
                query = "SELECT category, COUNT(*) as count FROM feedbacks WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 day' GROUP BY category"
            elif period == 'week':
                query = "SELECT category, COUNT(*) as count FROM feedbacks WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days' GROUP BY category"
            else:
                query = "SELECT category, COUNT(*) as count FROM feedbacks GROUP BY category"

            await cur.execute(query)
            rows = await cur.fetchall()
            return [(row['category'], row['count']) for row in rows] if rows else []

    async def get_feedback(self, feedback_id: int) -> dict | None:
        async with self.conn.cursor() as cur:
            await cur.execute("SELECT * FROM feedbacks WHERE id = %s", (feedback_id,))
            return await cur.fetchone()

    async def add_reply(self, feedback_id: int, admin_id: int, reply_text: str) -> int:
        async with self.conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO replies (feedback_id, admin_id, reply_text) VALUES (%s, %s, %s) RETURNING id",
                (feedback_id, admin_id, reply_text)
            )
            reply_id = (await cur.fetchone())["id"]
            await self.conn.commit()
        return reply_id

db = DB()
