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
            name TEXT,
            phone TEXT,
            balance NUMERIC(18,2) DEFAULT 0,
            onboarding_step INT DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            title TEXT,
            category TEXT,
            amount_uzs BIGINT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
