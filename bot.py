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
#                             START
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
#                      LANGUAGE BUTTONS
# ============================================================
@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(q: CallbackQuery):
    lang = q.data.split("_")[1]
    await set_lang(q.from_user.id, lang)
    await q.message.edit_text(LANG[lang]["welcome"])
    await q.answer()


# ============================================================
#                             STAT
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
#                             BALANCE
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
#                             HISTORY
# ============================================================
async def get_last_transactions(user_id: int, limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT title, category, amount_uzs, created_at, is_income
            FROM transactions
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """, user_id, limit)


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
#                    SAVE TRANSACTION
# ============================================================
async def save_transaction(user_id, title, amount, category, is_income):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs, is_income)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, title, category, amount, is_income)


# ============================================================
#            MAIN TEXT/VOICE PROCESSING LOGIC
# ============================================================
async def process_text(msg: Message, text: str):
    user_id = msg.from_user.id
    lang = await get_lang(user_id)
    original_text = (text or "").lower().strip()

    # debug log
    def dbg_write(s: str):
        try:
            with open("debug.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | {s}\n")
        except:
            pass

    dbg_write(f"INCOMING: user={user_id} text={text}")

    # 1) локальный парсер
    parsed = parse_expense(text)
    dbg_write(f"PARSED: {parsed}")

    title = "Операция"
    amount = 0
    category = "other"
    is_income = False

    if parsed:
        # parse_expense вернул (title, amount, category, detected_lang)
        try:
            title, amount, category, _ = parsed
        except Exception:
            # на случай других форматов
            dbg_write(f"PARSE_ERROR: unexpected parsed format: {parsed}")
            parsed = None

        if parsed:
            is_income = (category == "income")

    if not parsed:
        # 2) AI-анализ
        ai = await analyze_message(text)
        dbg_write(f"AI: {ai}")

        if not ai:
            await msg.answer(LANG[lang]["bad_format"])
            return

        title = ai.get("title", title)
        try:
            amount = int(ai.get("amount", 0))
        except:
            amount = 0
        category = ai.get("category", category)
        is_income = bool(ai.get("is_income", False))

    # 3) fallback: извлекаем сумму из оригинального текста, если нужно
    if not amount or amount <= 0:
        extracted = normalize_text_to_number(text) or 0
        if extracted > 0:
            dbg_write(f"EXTRACTED_FROM_TEXT: {extracted}")
            amount = extracted

    # 4) умная проверка ключевых слов (всегда выполняем)
    income_words = [
        "плюс", "+", "получил", "получила", "получилa", "зарплата", "зп", "з.п", "oylik",
        "maosh", "з/п", "зп.", "keldi", "kelib", "kelib tushdi", "добавь",
        "add", "qo'sh", "qosh", "qo‘sh", "поступил", "пришло", "пришёл", "пришла"
    ]

    expense_words = [
        "минус", "-", "расход", "потратил", "потратила", "такси",
        "еда", "chiqim", "avoqat", "купил", "оплатил", "снял"
    ]

    # если найдены слова, то они имеют приоритет и переопределяют is_income
    if any(w in original_text for w in income_words):
        dbg_write("KEYWORD_HINT: income")
        is_income = True
    if any(w in original_text for w in expense_words):
        dbg_write("KEYWORD_HINT: expense")
        is_income = False

    # 5) ещё дополнительная эвристика: если category явно "income" или "salary" — форсируем
    if category and category.lower() in ("income", "salary", "oylik", "maosh"):
        dbg_write(f"CATEGORY_HINT: {category} -> income")
        is_income = True

    # 6) финальная валидация суммы
    if not amount or amount <= 0:
        await msg.answer(LANG[lang]["bad_format"])
        dbg_write("FINAL: bad_format (amount<=0)")
        return

    # 7) сохраняем
    await save_transaction(user_id, title, amount, category or "other", is_income)
    dbg_write(f"SAVED: user={user_id} title={title} amount={amount} is_income={is_income} category={category}")

    # 8) ответ пользователю
    if is_income:
        ans = f"💰 Доход записан\n{title} — <b>{amount:,} UZS</b>"
    else:
        ans = f"📄 Расход записан\n{title} — <b>{amount:,} UZS</b>"

    await msg.answer(ans.replace(",", " "))

# ============================================================
#                           VOICE
# ============================================================
@dp.message(F.voice)
async def voice_handler(msg: Message):
    user_id = msg.from_user.id

    file_id = msg.voice.file_id
    path = f"voice_{user_id}.ogg"

    await download_voice(bot, file_id, path)

    text = await transcribe_voice(path)
    print("VOICE RAW TRANSCRIBE:", text)

    if os.path.exists(path):
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

