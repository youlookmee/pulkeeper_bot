import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
import os

# ==== OUR MODULES ====
from config import get_settings
from db import get_pool, init_db
from parser import CATEGORY_LABELS
from stats import get_stats, category_chart
from utils import lang_keyboard, balance_keyboard
from language import LANG

# AI functions
from ai import analyze_message, transcribe_voice

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# ===========================================
# LANGUAGE HELPERS
# ===========================================
async def set_lang(user_id, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET language=$1 WHERE id=$2", lang, user_id)


async def get_lang(uid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        lang = await conn.fetchval("SELECT language FROM users WHERE id=$1", uid)
    return lang or "ru"


# ===========================================
# START
# ===========================================
@dp.message(CommandStart())
async def start(msg: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id) VALUES ($1) ON CONFLICT DO NOTHING",
            msg.from_user.id,
        )

    await msg.answer(
        LANG["ru"]["choose_lang"],
        reply_markup=lang_keyboard()
    )


# ===========================================
# LANGUAGE CHOOSE
# ===========================================
@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(q: CallbackQuery):
    lang = q.data.split("_")[1]
    await set_lang(q.from_user.id, lang)
    await q.message.edit_text(LANG[lang]["welcome"])


# ===========================================
# STATISTICS (TEXT)
# ===========================================
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


# ===========================================
# STATISTICS IMAGE
# ===========================================
@dp.message(Command("stat_img"))
async def stat_img(msg: Message):
    lang = await get_lang(msg.from_user.id)
    file = await category_chart(msg.from_user.id)

    if not file:
        await msg.answer(LANG[lang]["no_data"])
        return

    await msg.answer_photo(file, caption=LANG[lang]["stat_title"])


# ===========================================
# BALANCE
# ===========================================
@dp.message(Command("balance"))
async def balance_handler(msg: Message):
    user_id = msg.from_user.id
    lang = await get_lang(user_id)

    pool = await get_pool()
    async with pool.acquire() as conn:
        income = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_uzs),0) FROM transactions WHERE user_id=$1 AND is_income=true",
            user_id
        )
        expense = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_uzs),0) FROM transactions WHERE user_id=$1 AND is_income=false",
            user_id
        )

    balance = income - expense

    text = (
        f"{LANG[lang]['balance_title']}:\n"
        f"<b>{balance:,} UZS</b>"
    ).replace(",", " ")

    await msg.answer(text, reply_markup=balance_keyboard(lang))


# ===========================================
# HISTORY
# ===========================================
async def get_last_transactions(uid, limit=20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT title, category, amount_uzs, created_at, is_income
            FROM transactions
            WHERE user_id=$1
            ORDER BY created_at DESC
            LIMIT $2
        """, uid, limit)
    return rows


@dp.message(Command("history"))
async def history_cmd(msg: Message):
    await send_history(msg.from_user.id, msg)


@dp.callback_query(F.data == "history")
async def history_cb(q: CallbackQuery):
    await send_history(q.from_user.id, q.message)
    await q.answer()


async def send_history(uid, target):
    lang = await get_lang(uid)
    rows = await get_last_transactions(uid)

    if not rows:
        await target.answer(LANG[lang]["history_empty"])
        return

    lines = [LANG[lang]["history_title"]]

    for r in rows:
        dt: datetime = r["created_at"]
        date = dt.strftime("%Y-%m-%d")
        amount = int(r["amount_uzs"])
        category = r["category"]
        income = r["is_income"]

        sign = "➕" if income else "➖"
        emoji = "💰" if income else "📉"

        lines.append(
            f"{date} · {emoji} {category} — {amount:,} UZS"
            .replace(",", " ")
        )

    await target.answer("\n".join(lines))


# ===========================================
# PROCESS TEXT MESSAGE (EXPENSE / INCOME)
# ===========================================
async def process_text(msg: Message, text: str):
    parsed = await analyze_message(text)

    if not parsed:
        await msg.answer("⚠️ Я не смог понять. Напишите сумму, пример:\nТакси 18000")
        return

    title = parsed.get("title")
    amount = parsed.get("amount")
    category_key = parsed.get("category", "other")
    op_type = parsed.get("type", "expense")

    is_income = (op_type == "income")

    category = CATEGORY_LABELS.get(category_key, CATEGORY_LABELS["other"])["ru"]

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs, is_income)
            VALUES ($1,$2,$3,$4,$5)
        """, msg.from_user.id, title, category, amount, is_income)

    if is_income:
        await msg.answer(f"💰 Доход записан\n{title} — <b>{amount:,} UZS</b>".replace(",", " "))
    else:
        await msg.answer(f"📉 Расход записан\n{title} — <b>{amount:,} UZS</b>".replace(",", " "))


# ===========================================
# VOICE MESSAGES
# ===========================================
@dp.message(F.voice)
async def voice_handler(msg: Message):
    uid = msg.from_user.id

    file_id = msg.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path

    local_file = f"voice_{uid}.ogg"
    await bot.download_file(file_path, local_file)

    # Расшифровываем аудио
    text = await transcribe_voice(local_file)

    if not text:
        await msg.answer("⚠️ Не удалось распознать голос. Попробуйте снова.")
        return

    await process_text(msg, text)


# ===========================================
# TEXT MESSAGES
# ===========================================
@dp.message(F.text)
async def text_handler(msg: Message):
    await process_text(msg, msg.text)


# ===========================================
# MAIN
# ===========================================
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
