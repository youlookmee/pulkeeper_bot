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
        total_spent = await conn.fetchval("""
            SELECT COALESCE(SUM(amount_uzs), 0)
            FROM transactions
            WHERE user_id = $1
        """, msg.from_user.id)

    text = (
        f"{LANG[lang]['balance_title']}:\n"
        f"{int(total_spent):,} UZS"
    ).replace(",", " ")

    await msg.answer(text, reply_markup=balance_keyboard(lang))


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

@dp.message(F.text)
async def exp(msg: Message):

    # Запускаем DeepSeek анализ текста
    ai_res = await analyze_message(msg.text)
    print("AI RESULT:", ai_res)

    if not ai_res or "amount" not in ai_res:
        await msg.answer("⚠️ Я не смог понять сумму. Пример: такси 30000")
        return

    title = ai_res.get("title") or "other"
    category_key = ai_res.get("category") or "other"

    try:
        amt = int(ai_res["amount"])
    except:
        await msg.answer("⚠️ Напишите сумму числом. Например: кофе 15000")
        return

    lang = await get_lang(msg.from_user.id)
    category_label = CATEGORY_LABELS.get(category_key, CATEGORY_LABELS["other"])[lang]

    # сохраняем в БД
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs)
            VALUES ($1,$2,$3,$4)
        """, msg.from_user.id, title, category_key, amt)

    # ответ пользователю
    text = {
        "ru": f"🛡 Расход записан\n{category_label} — <b>{amt:,} UZS</b>",
        "uz": f"🛡 Xarajat yozildi\n{category_label} — <b>{amt:,} UZS</b>",
        "en": f"🛡 Expense recorded\n{category_label} — <b>{amt:,} UZS</b>",
    }[lang].replace(",", " ")

    await msg.answer(text)


# -------------------- MAIN --------------------

async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
