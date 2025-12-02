import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import get_settings
from db import get_pool, init_db
from parser import parse_expense
from stats import get_stats, category_chart
from language import LANG
from utils import lang_keyboard, balance_keyboard
from parser import CATEGORY_LABELS
from datetime import datetime

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


async def set_lang(user_id, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET language=$1 WHERE id=$2",
            lang, user_id,
        )


async def get_lang(uid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        lang = await conn.fetchval("SELECT language FROM users WHERE id=$1", uid)
    return lang or "uz"


# -------------------- START --------------------
@dp.message(CommandStart())
async def start(msg: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id) VALUES ($1) ON CONFLICT DO NOTHING",
            msg.from_user.id,
        )
    await msg.answer(
        LANG["uz"]["choose_lang"],
        reply_markup=lang_keyboard()
    )


# -------------------- LANGUAGE --------------------
@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(q: CallbackQuery):
    lang = q.data.split("_")[1]
    await set_lang(q.from_user.id, lang)
    await q.message.edit_text(LANG[lang]["welcome"])


# -------------------- STATISTICS TEXT --------------------
@dp.message(Command("stat"))
async def stat(msg: Message):
    lang = await get_lang(msg.from_user.id)
    t, w, m = await get_stats(msg.from_user.id)

    text = (
        f"{LANG[lang]['stat_title']}\n\n"
        f"{LANG[lang]['today']}: <b>{t:,} UZS</b>\n"
        f"{LANG[lang]['week']}: <b>{w:,} UZS</b>\n"
        f"{LANG[lang]['month']}: <b>{m:,} UZS</b>\n"
    ).replace(",", " ")

    await msg.answer(text)

# -------------------- STATISTICS IMAGE --------------------
@dp.message(Command("stat_img"))
async def stat_img(msg: Message):
    lang = await get_lang(msg.from_user.id)
    file = await category_chart(msg.from_user.id)

    if not file:
        await msg.answer(LANG[lang]["no_data"])
        return

    await msg.answer_photo(file, caption=LANG[lang]["stat_title"])

# -------------------- BALANCE --------------------
@dp.message(Command("balance"))
async def balance_handler(msg: Message):
    lang = await get_lang(msg.from_user.id)

    pool = await get_pool()
    async with pool.acquire() as conn:
        total_spent = await conn.fetchval(
            """
            SELECT COALESCE(SUM(amount_uzs), 0)
            FROM transactions
            WHERE user_id = $1
            """,
            msg.from_user.id,
        )

    # Здесь пока баланс = просто суммарные расходы (без стартового капитала)
    # Позже можно сделать: баланс = стартовый_баланс - total_spent

    text = (
        f"{LANG[lang]['balance_title']}:\n"
        f"{int(total_spent):,} UZS"
    ).replace(",", " ")

    await msg.answer(text, reply_markup=balance_keyboard(lang))

# -------------------- HISTORY --------------------
async def get_last_transactions(user_id: int, limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT title, category, amount_uzs, created_at
            FROM transactions
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
    return rows

@dp.message(Command("history"))
async def history_command(msg: Message):
    await send_history(msg.from_user.id, msg)

@dp.callback_query(F.data == "history")
async def history_callback(q: CallbackQuery):
    await send_history(q.from_user.id, q.message)
    await q.answer()

async def send_history(user_id: int, target_message: Message):
    lang = await get_lang(user_id)
    rows = await get_last_transactions(user_id)

    if not rows:
        await target_message.answer(LANG[lang]["history_empty"])
        return

    lines = [LANG[lang]["history_title"]]
    for row in rows:
        title = row["title"]
        category = row["category"] or ""
        amount = int(row["amount_uzs"])
        dt: datetime = row["created_at"]
        date_str = dt.strftime("%Y-%m-%d")

        # строка вида: 2025-12-02 · 🍽 Еда — 25 000 UZS
        if category:
            line = f"{date_str} · {category} — {amount:,} UZS"
        else:
            line = f"{date_str} · {title} — {amount:,} UZS"

        lines.append(line.replace(",", " "))

    await target_message.answer("\n".join(lines))

# -------------------- ADD EXPENSE --------------------
@dp.message(F.text)
async def exp(msg: Message):
    parsed = parse_expense(msg.text)

    if not parsed:
        await msg.answer("⚠️ Error: amount missing")
        return

    title, amt, category_key, lang_detected = parsed

    category = CATEGORY_LABELS.get(category_key, CATEGORY_LABELS["other"])[lang_detected]

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs)
            VALUES ($1,$2,$3,$4)
        """, msg.from_user.id, title, category_key, amt)

    text = {
        "ru": f"🛡 Расход записан\n{category} — <b>{amt:,} UZS</b>",
        "uz": f"🛡 Xarajat yozildi\n{category} — <b>{amt:,} UZS</b>",
        "en": f"🛡 Expense recorded\n{category} — <b>{amt:,} UZS</b>",
    }[lang_detected].replace(",", " ")

    await msg.answer(text)

# -------------------- MAIN --------------------
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
