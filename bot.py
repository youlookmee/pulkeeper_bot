import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import get_settings
from db import get_pool, init_db
from parser import CATEGORY_LABELS
from stats import get_stats, category_chart
from language import LANG
from utils import lang_keyboard, balance_keyboard
from ai import analyze_message   # ← DeepSeek

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# -------------------- LANGUAGE SYSTEM --------------------

async def set_lang(uid, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET language=$1 WHERE id=$2",
            lang, uid
        )


async def get_lang(uid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        lang = await conn.fetchval(
            "SELECT language FROM users WHERE id=$1", uid
        )
    return lang or "uz"


# -------------------- /start --------------------

@dp.message(CommandStart())
async def start(msg: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id) VALUES ($1)
            ON CONFLICT DO NOTHING
        """, msg.from_user.id)

    await msg.answer(
        LANG["uz"]["choose_lang"],
        reply_markup=lang_keyboard()
    )


# -------------------- LANGUAGE SELECTION --------------------

@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(q: CallbackQuery):
    lang = q.data.split("_")[1]
    await set_lang(q.from_user.id, lang)

    await q.message.edit_text(LANG[lang]["welcome"])
    await q.answer()


# -------------------- STAT TEXT --------------------

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


# -------------------- STAT IMAGE --------------------

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
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(CASE WHEN is_income THEN amount_uzs END), 0) AS income,
                COALESCE(SUM(CASE WHEN NOT is_income THEN amount_uzs END), 0) AS expense
            FROM transactions
            WHERE user_id = $1
            """,
            msg.from_user.id,
        )

    income = int(row["income"])
    expense = int(row["expense"])
    balance = income - expense

    text = (
        f"💰 Доходы: <b>{income:,} UZS</b>\n"
        f"💸 Расходы: <b>{expense:,} UZS</b>\n"
        f"📊 Баланс: <b>{balance:,} UZS</b>"
    ).replace(",", " ")

    await msg.answer(text)



# -------------------- HISTORY --------------------

async def get_last_transactions(uid, limit=20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT title, category, amount_uzs, created_at
            FROM transactions
            WHERE user_id=$1
            ORDER BY created_at DESC
            LIMIT $2
        """, uid, limit)
    return rows


@dp.message(Command("history"))
async def history_command(msg: Message):
    await send_history(msg.from_user.id, msg)


@dp.callback_query(F.data == "history")
async def history_callback(q: CallbackQuery):
    await send_history(q.from_user.id, q.message)
    await q.answer()


async def send_history(uid: int, target):
    lang = await get_lang(uid)
    rows = await get_last_transactions(uid)

    if not rows:
        await target.answer(LANG[lang]["history_empty"])
        return

    lines = [LANG[lang]["history_title"]]

    for row in rows:
        dt: datetime = row["created_at"]
        date_str = dt.strftime("%Y-%m-%d")
        amount = int(row["amount_uzs"])
        category = row["category"]
        title = row["title"]

        if category:
            line = f"{date_str} · {category} — {amount:,} UZS"
        else:
            line = f"{date_str} · {title} — {amount:,} UZS"

        lines.append(line.replace(",", " "))

    await target.answer("\n".join(lines))


# -------------------- ADD EXPENSE (DeepSeek) --------------------

# -------------------- ADD EXPENSE / INCOME --------------------
@dp.message(F.text)
async def exp(msg: Message):
    ai_data = await analyze_message(msg.text)

    if not ai_data:
        await msg.answer("⚠️ Я не смог понять сумму. Пример: такси 30000")
        return

    title = ai_data.get("title")
    amount = ai_data.get("amount")
    category = ai_data.get("category")
    is_income = ai_data.get("is_income", False)

    if not amount:
        await msg.answer("⚠️ Я не смог определить сумму.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO transactions (user_id, title, category, amount_uzs, is_income)
            VALUES ($1,$2,$3,$4,$5)
            """,
            msg.from_user.id,
            title,
            category,
            amount,
            is_income
        )

    # Ответ пользователю
    if is_income:
        text = f"💰 Доход записан\n<b>{title}</b> — <b>{amount:,} UZS</b>"
    else:
        text = f"🧾 Расход записан\n<b>{title}</b> — <b>{amount:,} UZS</b>"

    await msg.answer(text.replace(",", " "))

# -------------------- MAIN --------------------

async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
