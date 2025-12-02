import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from config import get_settings
from db import get_pool, init_db
from parser import parse_expense
from stats import get_stats, category_chart
from language import LANG
from utils import lang_keyboard

settings = get_settings()
bot = Bot(settings.bot_token, parse_mode="HTML")
dp = Dispatcher()

async def set_lang(user_id, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET language=$1 WHERE id=$2", lang, user_id
        )

async def get_lang(uid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT language FROM users WHERE id=$1", uid
        ) or "uz"

@dp.message(CommandStart())
async def start(msg: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id) VALUES ($1) ON CONFLICT DO NOTHING",
            msg.from_user.id,
        )
    await msg.answer(LANG["uz"]["choose_lang"], reply_markup=lang_keyboard())

@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(q: CallbackQuery):
    lang = q.data.split("_")[1]
    await set_lang(q.from_user.id, lang)
    await q.message.edit_text(LANG[lang]["welcome"])

@dp.message(Command("stat"))
async def stat(msg: Message):
    lang = await get_lang(msg.from_user.id)
    t,w,m = await get_stats(msg.from_user.id)
    text = (
        f"{LANG[lang]['stat_title']}\n\n"
        f"{LANG[lang]['today']}: {t:,} UZS\n"
        f"{LANG[lang]['week']}: {w:,} UZS\n"
        f"{LANG[lang]['month']}: {m:,} UZS\n"
    ).replace(",", " ")
    await msg.answer(text)

@dp.message(Command("stat_img"))
async def stat_img(msg: Message):
    lang = await get_lang(msg.from_user.id)
    file = await category_chart(msg.from_user.id)
    if not file:
        await msg.answer(LANG[lang]["no_data"])
        return
    await msg.answer_photo(file, caption=LANG[lang]["stat_title"])

@dp.message(F.text)
async def exp(msg: Message):
    lang = await get_lang(msg.from_user.id)
    p = parse_expense(msg.text)
    if not p:
        await msg.answer(LANG[lang]["bad_amount"])
        return
    title, amt = p
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO transactions (user_id,title,amount_uzs)
        VALUES ($1,$2,$3)
        """, msg.from_user.id, title, amt)
    await msg.answer(LANG[lang]["added"])

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
