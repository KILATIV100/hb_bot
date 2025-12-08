# database/db.py — тепер на psycopg3 (binary = без компіляції)
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta
from typing import List, Tuple
from config import settings

class DB:
    def __init__(self):
        self.dsn = settings.DATABASE_URL

    async def connect(self):
        self.conn = await psycopg.AsyncConnection.connect(self.dsn, row_factory=dict_row)
        await self.create_tables()

    async def create_tables(self):
        async with self.conn.cursor() as cur:
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    category TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content TEXT
                )
            ''')
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id BIGINT PRIMARY KEY,
                    last_feedback TIMESTAMP
                )
            ''')
            await self.conn.commit()

        async def add_feedback(self, user_id: int, username: str, category: str, content: str):
        async with self.conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO feedbacks (user_id, username, category, content) 
                   VALUES (%s, %s, %s, %s)""",
                (user_id, username, category, content)
            )
            await cur.execute(
                """INSERT INTO rate_limits (user_id, last_feedback) 
                   VALUES (%s, CURRENT_TIMESTAMP) 
                   ON CONFLICT (user_id) DO UPDATE SET last_feedback = CURRENT_TIMESTAMP""",
                (user_id,)
            )
            await self.conn.commit()

    async def check_rate_limit(self, user_id: int) -> bool:
        async with self.conn.cursor() as cur:
            await cur.execute(
                "SELECT last_feedback FROM rate_limits WHERE user_id = %s", (user_id,)
            )
            row = await cur.fetchone()
            if row and row["last_feedback"]:
                delta = datetime.utcnow() - row["last_feedback"]
                if delta.total_seconds() < 300:  # 5 хвилин
                    return False
        return True

    async def get_stats(self, period: str = 'day') -> List[Tuple[str, int]]:
        now = datetime.utcnow()
        if period == 'day':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = datetime.min.replace(tzinfo=None)

        async with self.conn.cursor() as cur:
            await cur.execute(
                "SELECT category, COUNT(*) as count FROM feedbacks WHERE timestamp >= %s GROUP BY category",
                (start,)
            )
            rows = await cur.fetchall()
        return [(row["category"], row["count"]) for row in rows]

db = DB()
