import asyncpg
from config import get_settings

settings = get_settings()
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.db_url)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            language VARCHAR(5) DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id),
            title TEXT,
            category TEXT,
            amount_uzs NUMERIC(18,2) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
