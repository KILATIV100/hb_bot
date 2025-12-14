# database/db.py — ВИПРАВЛЕНА ВЕРСІЯ (З CONNECTION POOL)
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from datetime import datetime
from config import settings

class DB:
    def __init__(self):
        self.dsn = settings.DATABASE_URL
        self.pool = None

    async def connect(self):
        """Створює пул з'єднань до бази даних"""
        # Створюємо пул. row_factory передаємо в kwargs, щоб отримувати результати як словники
        self.pool = AsyncConnectionPool(
            conninfo=self.dsn,
            min_size=1,
            max_size=20,  # Максимальна кількість одночасних з'єднань
            kwargs={"row_factory": dict_row}
        )
        await self.pool.open()
        await self.create_tables()

    async def close(self):
        """Закриває пул з'єднань при зупинці бота"""
        if self.pool:
            await self.pool.close()

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
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Додавання колонок, якщо їх немає (міграції на льоту)
                await cur.execute('''
                    ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS photo_file_id TEXT
                ''')
                await cur.execute('''
                    ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS video_file_id TEXT
                ''')
                await cur.execute('''
                    ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS document_file_id TEXT
                ''')
                await cur.execute('''
                    ALTER TABLE feedbacks ADD COLUMN IF NOT EXISTS group_message_id INT
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
            # Commit відбувається автоматично при виході з контекстного менеджера connection

    async def add_feedback(self, user_id: int, username: str, category: str, content: str,
                          photo_file_id: str | None = None, video_file_id: str | None = None,
                          document_file_id: str | None = None) -> int:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO feedbacks (user_id, username, category, content, photo_file_id, video_file_id, document_file_id) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (user_id, username, category, content, photo_file_id, video_file_id, document_file_id)
                )
                feedback_id = (await cur.fetchone())["id"]
                
                await cur.execute(
                    "INSERT INTO rate_limits (user_id, last_feedback) VALUES (%s, CURRENT_TIMESTAMP) ON CONFLICT (user_id) DO UPDATE SET last_feedback = CURRENT_TIMESTAMP",
                    (user_id,)
                )
        return feedback_id

    async def check_rate_limit(self, user_id: int) -> bool:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_feedback FROM rate_limits WHERE user_id = %s", (user_id,))
                row = await cur.fetchone()
                if row and (datetime.utcnow() - row["last_feedback"]).total_seconds() < 60:
                    return False
        return True

    async def get_stats(self, period: str) -> list:
        """Отримати статистику за період: 'day', 'week', 'all'"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                if period == 'day':
                    query = '''
                        SELECT category, COUNT(*) as count
                        FROM feedbacks
                        WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 day'
                        GROUP BY category
                    '''
                elif period == 'week':
                    query = '''
                        SELECT category, COUNT(*) as count
                        FROM feedbacks
                        WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                        GROUP BY category
                    '''
                else:  # 'all'
                    query = '''
                        SELECT category, COUNT(*) as count
                        FROM feedbacks
                        GROUP BY category
                    '''

                await cur.execute(query)
                rows = await cur.fetchall()
                return [(row['category'], row['count']) for row in rows] if rows else []

    async def get_feedback(self, feedback_id: int) -> dict | None:
        """Отримати feedback за ID"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM feedbacks WHERE id = %s", (feedback_id,))
                return await cur.fetchone()

    async def add_reply(self, feedback_id: int, admin_id: int, reply_text: str) -> int:
        """Додати відповідь адміна"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO replies (feedback_id, admin_id, reply_text) VALUES (%s, %s, %s) RETURNING id",
                    (feedback_id, admin_id, reply_text)
                )
                reply_id = (await cur.fetchone())["id"]
        return reply_id

    async def update_group_message_id(self, feedback_id: int, group_message_id: int) -> None:
        """Оновити group_message_id для feedback"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE feedbacks SET group_message_id = %s WHERE id = %s",
                    (group_message_id, feedback_id)
                )

    async def get_feedback_by_group_message_id(self, group_message_id: int) -> dict | None:
        """Отримати feedback за group_message_id (для reply в групі)"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM feedbacks WHERE group_message_id = %s", (group_message_id,))
                return await cur.fetchone()

db = DB()
