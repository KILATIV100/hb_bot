# database/db.py
import psycopg
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from datetime import datetime, timezone
from config import settings
import logging

# Налаштування логування для БД
logger = logging.getLogger(__name__)

class DB:
    def __init__(self):
        self.dsn = settings.DATABASE_URL
        self.pool = None

    async def connect(self):
        """Створює пул з'єднань з базою даних"""
        try:
            self.pool = AsyncConnectionPool(
                conninfo=self.dsn,
                open=False,
                kwargs={"row_factory": dict_row} # Для psycopg 3.x
            )
            await self.pool.open()
            logger.info("✅ Підключення до БД успішне (Connection Pool)")
            await self.create_tables()
        except Exception as e:
            logger.error(f"❌ Критична помилка підключення до БД: {e}")
            raise e

    async def create_tables(self):
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS feedbacks (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        category TEXT,
                        content TEXT,
                        photo_file_id TEXT,
                        video_file_id TEXT,
                        document_file_id TEXT,
                        group_message_id INT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
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
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS media (
                        id SERIAL PRIMARY KEY,
                        feedback_id INT REFERENCES feedbacks(id) ON DELETE CASCADE,
                        file_id TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Перевірка та додавання колонок, якщо їх немає (міграції на льоту)
                for col in ['photo_file_id', 'video_file_id', 'document_file_id']:
                    await cur.execute(f'''
                        ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS {col} TEXT
                    ''')
                await cur.execute('''
                    ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS group_message_id INT
                ''')
            # pool.connection() автоматично робить commit при виході з контексту, якщо не було помилок

    async def add_feedback(self, user_id: int, username: str, category: str, content: str,
                          photo_file_id: str | None = None, video_file_id: str | None = None,
                          document_file_id: str | None = None) -> int:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO feedbacks 
                    (user_id, username, category, content, photo_file_id, video_file_id, document_file_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (user_id, username, category, content, photo_file_id, video_file_id, document_file_id)
                )
                feedback_id = (await cur.fetchone())["id"]
                
                await cur.execute(
                    """INSERT INTO rate_limits (user_id, last_feedback) 
                    VALUES (%s, CURRENT_TIMESTAMP) 
                    ON CONFLICT (user_id) DO UPDATE SET last_feedback = CURRENT_TIMESTAMP""",
                    (user_id,)
                )
        return feedback_id

    async def check_rate_limit(self, user_id: int) -> bool:
        """Повертає True, якщо можна писати. False, якщо треба чекати."""
        # АНТИСПАМ ВИМКНЕНО - завжди повертає True
        return True

        # async with self.pool.connection() as conn:
        #     async with conn.cursor() as cur:
        #         await cur.execute("SELECT last_feedback FROM rate_limits WHERE user_id = %s", (user_id,))
        #         row = await cur.fetchone()
        #         if row:
        #             last_time = row["last_feedback"]
        #             # Якщо база повертає naive datetime, вважаємо це UTC
        #             if last_time.tzinfo is None:
        #                 last_time = last_time.replace(tzinfo=timezone.utc)
        #
        #             diff = (datetime.now(timezone.utc) - last_time).total_seconds()
        #             if diff < 60:
        #                 return False
        # return True

    async def get_stats(self, period: str) -> list:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
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
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM feedbacks WHERE id = %s", (feedback_id,))
                return await cur.fetchone()

    async def add_reply(self, feedback_id: int, admin_id: int, reply_text: str) -> int:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO replies (feedback_id, admin_id, reply_text) VALUES (%s, %s, %s) RETURNING id",
                    (feedback_id, admin_id, reply_text)
                )
                reply_id = (await cur.fetchone())["id"]
        return reply_id

    async def update_group_message_id(self, feedback_id: int, group_message_id: int) -> None:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE feedbacks SET group_message_id = %s WHERE id = %s",
                    (group_message_id, feedback_id)
                )

    async def get_feedback_by_group_message_id(self, group_message_id: int) -> dict | None:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM feedbacks WHERE group_message_id = %s", (group_message_id,))
                return await cur.fetchone()

    async def add_media(self, feedback_id: int, file_id: str, file_type: str) -> int:
        """Додає медіа файл до feedback"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO media (feedback_id, file_id, file_type) VALUES (%s, %s, %s) RETURNING id",
                    (feedback_id, file_id, file_type)
                )
                media_id = (await cur.fetchone())["id"]
        return media_id

    async def get_feedback_media(self, feedback_id: int) -> list:
        """Повертає всі медіа файли для feedback"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT file_id, file_type FROM media WHERE feedback_id = %s ORDER BY id",
                    (feedback_id,)
                )
                rows = await cur.fetchall()
                return [{'file_id': row['file_id'], 'file_type': row['file_type']} for row in rows] if rows else []

    async def get_last_feedback_id(self, user_id: int) -> int | None:
        """Повертає ID останнього feedback від користувача"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM feedbacks WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1",
                    (user_id,)
                )
                row = await cur.fetchone()
                return row["id"] if row else None

db = DB()
