import matplotlib.pyplot as plt
from io import BytesIO
from aiogram.types import FSInputFile
from db import get_pool

plt.style.use("dark_background")

async def get_stats(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        t = await conn.fetchval("""
        SELECT COALESCE(SUM(amount_uzs),0)
        FROM transactions
        WHERE user_id=$1 AND created_at::date=CURRENT_DATE
        """, user_id)

        w = await conn.fetchval("""
        SELECT COALESCE(SUM(amount_uzs),0)
        FROM transactions
        WHERE user_id=$1 AND created_at>=CURRENT_DATE-INTERVAL '7 days'
        """, user_id)

        m = await conn.fetchval("""
        SELECT COALESCE(SUM(amount_uzs),0)
        FROM transactions
        WHERE user_id=$1 AND date_trunc('month', created_at)=date_trunc('month', CURRENT_DATE)
        """, user_id)

    return int(t), int(w), int(m)

async def category_chart(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
        SELECT COALESCE(category,'Other') AS cat, SUM(amount_uzs) AS s
        FROM transactions
        WHERE user_id=$1
        GROUP BY cat
        """, user_id)

    if not rows:
        return None

    labels = [r["cat"] for r in rows]
    values = [float(r["s"]) for r in rows]

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return FSInputFile(buf, "chart.png")
