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
from utils import lang_keyboard


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


# -------------------- ADD EXPENSE --------------------
@dp.message(F.text)
async def exp(msg: Message):
    lang = await get_lang(msg.from_user.id)
    parsed = parse_expense(msg.text)

    if not parsed:
        await msg.answer(LANG[lang]["bad_amount"])
        return

    title, amt, category = parsed

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id,title,category,amount_uzs)
            VALUES ($1,$2,$3,$4)
        """, msg.from_user.id, title, category, amt)

    await msg.answer(
        f"🛡 {LANG[lang]['added']}\n"
        f"{category} — <b>{amt:,} UZS</b>".replace(",", " ")
    )


# -------------------- MAIN --------------------
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
