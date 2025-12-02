# bot.py — PulKeeper v3.0 (Onboarding + AI Parser + Drafts + Confirm Buttons)

import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# Local imports
from config import get_settings
from db import get_pool, init_db
from states import Onboarding
from language import LANG
from utils import lang_keyboard, balance_keyboard

# AI + Draft + Keyboards
from ai import analyze_message
from draft import save_draft, get_draft, clear_draft
from keyboards import draft_keyboard

# Category labels (for history)
from parser import CATEGORY_LABELS

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


# ------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------

async def get_lang(uid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        lang = await conn.fetchval("SELECT language FROM users WHERE id=$1", uid)
        return lang or "ru"


async def set_lang(uid, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET language=$1 WHERE id=$2", lang, uid)


# ------------------------------------------------
# START / ONBOARDING
# ------------------------------------------------

@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    pool = await get_pool()

    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT onboarding_step FROM users WHERE id=$1", uid)

        if not user:
            await conn.execute("INSERT INTO users (id) VALUES ($1)", uid)
            step = 0
        else:
            step = user['onboarding_step']

    # Онбординг завершён
    if step >= 3:
        lang = await get_lang(uid)
        await msg.answer(LANG[lang]["welcome"])
        return

    # Шаг 1 — имя
    await msg.answer(
        "Привет! Я PulKeeper 🛡\n\nПомогу тебе вести учёт расходов.\n\nКак к тебе обращаться?"
    )
    await state.set_state(Onboarding.name)


@dp.message(Onboarding.name)
async def get_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    uid = msg.from_user.id

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET name=$1, onboarding_step=1 WHERE id=$2",
            name, uid
        )

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True
    )

    await msg.answer(
        f"Отлично, {name}!\nТеперь отправь свой номер телефона 👇",
        reply_markup=kb
    )

    await state.set_state(Onboarding.phone)


@dp.message(Onboarding.phone)
async def get_phone(msg: Message, state: FSMContext):
    if not msg.contact:
        await msg.answer("Пожалуйста, нажми кнопку и отправь номер.")
        return

    phone = msg.contact.phone_number
    uid = msg.from_user.id

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET phone=$1, onboarding_step=2 WHERE id=$2",
            phone, uid
        )

    await msg.answer(
        "Последний вопрос:\nСколько денег у тебя сейчас?\nНапример: 500000"
    )

    await state.set_state(Onboarding.balance)


@dp.message(Onboarding.balance)
async def get_balance(msg: Message, state: FSMContext):
    uid = msg.from_user.id

    try:
        balance = float(msg.text.replace(" ", ""))
    except:
        await msg.answer("Введите число, например: 500000")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance=$1, onboarding_step=3 WHERE id=$2",
            balance, uid
        )

    await state.clear()

    await msg.answer(
        f"Принято! Записал {int(balance):,} UZS как стартовый капитал 💼".replace(",", " ")
    )

    await msg.answer(
        "🎙 Как отправлять голосовые:\n"
        "1) Зажми микрофон\n"
        "2) Скажи расход: «такси 120000»\n"
        "3) Отпусти\n\n"
        "Попробуй — отправь любой расход 👇"
    )


# ------------------------------------------------
# AI PARSER — MAIN HANDLER
# ------------------------------------------------

@dp.message(F.text)
async def ai_handler(msg: Message):
    if msg.text.startswith("/"):
        return  # команды не трогаем

    uid = msg.from_user.id

    await msg.answer("📝 Обрабатываю сообщение...")

    ai_data = await analyze_message(msg.text)

    if not ai_data.get("valid"):
        await msg.answer(f"⚠ Не понял сообщение: {ai_data.get('reason')}")
        return

    # Сохраняем черновик
    save_draft(uid, ai_data)

    text = (
        "Новая транзакция\n"
        f"💸 Сумма: <b>{ai_data['amount']:,} UZS</b>\n"
        f"📂 Категория: {ai_data['category']}\n"
        f"📝 Описание: {ai_data['title']}\n"
        f"📅 Дата: {ai_data['date']}"
    ).replace(",", " ")

    await msg.answer(text, reply_markup=draft_keyboard())


# ------------------------------------------------
# DRAFT BUTTONS
# ------------------------------------------------

@dp.callback_query(F.data == "draft_accept")
async def accept_draft(q: CallbackQuery):
    uid = q.from_user.id
    data = get_draft(uid)

    if not data:
        await q.answer("Черновик не найден!", show_alert=True)
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs)
            VALUES ($1,$2,$3,$4)
        """,
        uid,
        data["title"],
        data["category"],
        data["amount"]
    )

    clear_draft(uid)

    await q.message.answer("✔ Транзакция добавлена!")
    await q.answer()


@dp.callback_query(F.data == "draft_decline")
async def decline_draft(q: CallbackQuery):
    clear_draft(q.from_user.id)
    await q.message.answer("❌ Транзакция отменена.")
    await q.answer()


@dp.callback_query(F.data == "draft_edit")
async def edit_draft(q: CallbackQuery):
    await q.message.answer("✏ Введите исправленный текст:")
    await q.answer()


# ------------------------------------------------
# STATS
# ------------------------------------------------

from stats import get_stats, category_chart

@dp.message(Command("stat"))
async def stat(msg: Message):
    uid = msg.from_user.id
    lang = await get_lang(uid)
    t, w, m = await get_stats(uid)

    text = (
        f"{LANG[lang]['stat_title']}\n\n"
        f"{LANG[lang]['today']}: <b>{int(t):,} UZS</b>\n"
        f"{LANG[lang]['week']}: <b>{int(w):,} UZS</b>\n"
        f"{LANG[lang]['month']}: <b>{int(m):,} UZS</b>\n"
    ).replace(",", " ")

    await msg.answer(text)


@dp.message(Command("stat_img"))
async def stat_img(msg: Message):
    uid = msg.from_user.id
    lang = await get_lang(uid)
    file = await category_chart(uid)

    if not file:
        await msg.answer(LANG[lang]["no_data"])
        return

    await msg.answer_photo(file, caption=LANG[lang]["stat_title"])


# ------------------------------------------------
# BALANCE
# ------------------------------------------------

@dp.message(Command("balance"))
async def balance_handler(msg: Message):
    uid = msg.from_user.id
    lang = await get_lang(uid)

    pool = await get_pool()
    async with pool.acquire() as conn:
        start_balance = await conn.fetchval(
            "SELECT COALESCE(balance,0) FROM users WHERE id=$1",
            uid
        )
        total_spent = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_uzs),0) FROM transactions WHERE user_id=$1",
            uid
        )

    current = float(start_balance) - float(total_spent)

    text = (
        f"{LANG[lang]['balance_title']}:\n"
        f"{int(current):,} UZS"
    ).replace(",", " ")

    await msg.answer(text, reply_markup=balance_keyboard(lang))


# ------------------------------------------------
# HISTORY
# ------------------------------------------------

async def get_last_transactions(uid, limit=20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT title, category, amount_uzs, created_at
            FROM transactions
            WHERE user_id=$1
            ORDER BY created_at DESC
            LIMIT $2
        """, uid, limit)


@dp.message(Command("history"))
async def history(msg: Message):
    uid = msg.from_user.id
    lang = await get_lang(uid)

    rows = await get_last_transactions(uid)
    if not rows:
        await msg.answer(LANG[lang]["history_empty"])
        return

    lines = [LANG[lang]["history_title"]]

    for row in rows:
        date_str = row["created_at"].strftime("%Y-%m-%d")
        category_label = CATEGORY_LABELS.get(row["category"], CATEGORY_LABELS["other"])[lang]
        line = f"{date_str} · {category_label} — {int(row['amount_uzs']):,} UZS"
        lines.append(line.replace(",", " "))

    await msg.answer("\n".join(lines))


# ------------------------------------------------
# MAIN
# ------------------------------------------------

async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
