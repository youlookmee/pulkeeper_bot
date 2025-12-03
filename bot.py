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
from ai import analyze_message, transcribe_voice, download_voice
from parser import parse_expense
from stats import get_stats, category_chart
from language import LANG
from keyboards import lang_keyboard, balance_keyboard
from utils_number import normalize_text_to_number


settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# ============================================================
#                      LANGUAGE STORAGE
# ============================================================
async def set_lang(user_id, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET language=$1 WHERE id=$2", lang, user_id)


async def get_lang(uid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        lang = await conn.fetchval("SELECT language FROM users WHERE id=$1", uid)
    return lang or "uz"


# ============================================================
#                           START
# ============================================================
@dp.message(CommandStart())
async def start(msg: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id) VALUES ($1) ON CONFLICT DO NOTHING",
            msg.from_user.id
        )

    await msg.answer(
        LANG["uz"]["choose_lang"],
        reply_markup=lang_keyboard()
    )


# ============================================================
#                     LANGUAGE BUTTON
# ============================================================
@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(q: CallbackQuery):
    lang = q.data.split("_")[1]
    await set_lang(q.from_user.id, lang)
    await q.message.edit_text(LANG[lang]["welcome"])
    await q.answer()


# ============================================================
#                           STAT
# ============================================================
@dp.message(Command("stat"))
async def stat(msg: Message):
    lang = await get_lang(msg.from_user.id)
    t, w, m = await get_stats(msg.from_user.id)

    text = (
        f"{LANG[lang]['stat_title']}\n\n"
        f"{LANG[lang]['today']}: <b>{t:,} UZS</b>\n"
        f"{LANG[lang]['week']}: <b>{w:,} UZS</b>\n"
        f"{LANG[lang]['month']}: <b>{m:,} UZS</b>"
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


# ============================================================
#                      BALANCE
# ============================================================
@dp.message(Command("balance"))
async def balance_handler(msg: Message):
    lang = await get_lang(msg.from_user.id)

    pool = await get_pool()
    async with pool.acquire() as conn:
        total_spent = await conn.fetchval("""
            SELECT COALESCE(SUM(amount_uzs), 0)
            FROM transactions
            WHERE user_id = $1 AND is_income = false
        """, msg.from_user.id)

        total_income = await conn.fetchval("""
            SELECT COALESCE(SUM(amount_uzs), 0)
            FROM transactions
            WHERE user_id = $1 AND is_income = true
        """, msg.from_user.id)

    balance = total_income - total_spent

    await msg.answer(
        f"{LANG[lang]['balance_title']}:\n<b>{balance:,} UZS</b>".replace(",", " "),
        reply_markup=balance_keyboard(lang)
    )


# ============================================================
#                       HISTORY
# ============================================================
async def get_last_transactions(user_id: int, limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT title, category, amount_uzs, created_at, is_income
            FROM transactions
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """, user_id, limit)
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
        icon = "💰" if row["is_income"] else "📄"
        kind = "Доход" if row["is_income"] else "Расход"

        lines.append(
            f"{icon} {kind} — {row['title']} · {row['amount_uzs']:,} UZS · {row['created_at'].strftime('%Y-%m-%d')}"
            .replace(",", " ")
        )

    await target_message.answer("\n".join(lines))


# ============================================================
#                     SAVE TRANSACTION
# ============================================================
async def save_transaction(user_id, title, amount, category, is_income):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs, is_income)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, title, category, amount, is_income)


# ============================================================
#               MAIN EXPENSE/INCOME HANDLER
# ============================================================
async def process_text(msg: Message, text: str):
    user_id = msg.from_user.id
    lang = await get_lang(user_id)
    original_text = text.lower()

    # ---------------------------------------
    # 1) Локальный быстрый парсер
    # ---------------------------------------
    parsed = parse_expense(text)

    if parsed:
        title, amount, category, _ = parsed
        is_income = (category == "income")

    else:
        # ---------------------------------------
        # 2) DeepSeek-анализ
        # ---------------------------------------
        ai = await analyze_message(text)

        if not ai:
            await msg.answer(LANG[lang]["bad_format"])
            return

        title = ai.get("title", "Операция")

        # AI amount
        ai_amount = ai.get("amount", 0)
        try:
            ai_amount = int(ai_amount)
        except:
            ai_amount = 0

        # Fallback извлекаем сумму из текста
        extracted = normalize_text_to_number(text) or 0

        # Самый надёжный вариант: берём максимум
        amount = max(ai_amount, extracted)

        if amount <= 0:
            await msg.answer(LANG[lang]["bad_format"])
            return

        # Категория
        category = ai.get("category", "other")
        is_income = bool(ai.get("is_income", False))

        # ---------------------------------------
        # 3) Дополнительная проверка ключевых слов
        # ---------------------------------------
        if any(w in original_text for w in ["плюс", "+", "получил", "oylik", "keldi", "kelib"]):
            is_income = True
        if any(w in original_text for w in ["минус", "-", "расход", "chiqim", "такси", "еда"]):
            is_income = False

    # ---------------------------------------
    # 4) Сохраняем
    # ---------------------------------------
    await save_transaction(user_id, title, amount, category, is_income)

    # ---------------------------------------
    # 5) Ответ пользователю
    # ---------------------------------------
    icon = "💰" if is_income else "📄"
    await msg.answer(
        f"{icon} {'Доход' if is_income else 'Расход'} записан\n{title} — <b>{amount:,} UZS</b>"
        .replace(",", " ")
    )


# ============================================================
#                           VOICE
# ============================================================
@dp.message(F.voice)
async def voice_handler(msg: Message):
    user_id = msg.from_user.id

    file_id = msg.voice.file_id
    path = f"voice_{user_id}.ogg"

    await download_voice(bot, file_id,  

    text = await transcribe_voice(path)
    os.remove(path)

    if not text:
        await msg.answer("❗ Не смог распознать голосовое сообщение.")
        return

    await process_text(msg, text)


# ============================================================
#                           TEXT
# ============================================================
@dp.message(F.text)
async def text_handler(msg: Message):
    await process_text(msg, msg.text)


# ============================================================
#                           MAIN
# ============================================================
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
