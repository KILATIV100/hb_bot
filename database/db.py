# database/db.py (повністю async на asyncpg — для Railway Postgres, без лагів!)
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

class DB:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)
        await self.create_tables()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    category TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content TEXT
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id BIGINT PRIMARY KEY,
                    last_feedback TIMESTAMP
                )
            ''')

    async def add_feedback(self, user_id: int, category: str, content: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO feedbacks (user_id, category, content) VALUES ($1, $2, $3)',
                user_id, category, content
            )
            await conn.execute(
                'INSERT INTO rate_limits (user_id, last_feedback) VALUES ($1, CURRENT_TIMESTAMP) '
                'ON CONFLICT (user_id) DO UPDATE SET last_feedback = CURRENT_TIMESTAMP',
                user_id
            )

    async def check_rate_limit(self, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                'SELECT last_feedback FROM rate_limits WHERE user_id = $1', user_id
            )
            if result:
                last_time = result['last_feedback']
                if (datetime.now(last_time.tzinfo) - last_time).total_seconds() < 300:  # 5 хв
                    return False
            return True

    async def get_stats(self, period: str = 'day') -> List[Tuple[str, int]]:
        now = datetime.utcnow()  # UTC для Postgres
        if period == 'day':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = datetime.min

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT category, COUNT(*) as count FROM feedbacks WHERE timestamp >= $1 GROUP BY category',
                start
            )
        return [(row['category'], row['count']) for row in rows]

# Глобальний інстанс
db = DB(settings.DATABASE_URL)
