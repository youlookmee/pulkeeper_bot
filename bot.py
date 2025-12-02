# bot.py — PulKeeper v2.0 (full onboarding + balance + history)
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from config import get_settings
from db import get_pool, init_db
from parser import parse_expense, CATEGORY_LABELS
from stats import get_stats, category_chart
from language import LANG
from utils import lang_keyboard, balance_keyboard
from states import Onboarding

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Dispatcher с in-memory storage для FSM
dp = Dispatcher(storage=MemoryStorage())


# ---- helpers ----
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


# -------------------- START / ONBOARDING --------------------
@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT onboarding_step FROM users WHERE id=$1", msg.from_user.id)
        if not user:
            await conn.execute("INSERT INTO users (id) VALUES ($1) ON CONFLICT DO NOTHING", msg.from_user.id)
            step = 0
        else:
            step = user.get("onboarding_step", 0)

    # Если онбординг уже пройден — покажем обычный welcome (по сохранённому языку)
    if step >= 3:
        lang = await get_lang(msg.from_user.id)
        await msg.answer(LANG[lang]["welcome"])
        return

    # Начинаем онбординг: спрашиваем имя
    await msg.answer(
        "Привет! Я PulKeeper 🛡\n\nЯ помогу вести учёт расходов и доходов.\n\nКак к тебе обращаться?"
    )
    await state.set_state(Onboarding.name)


# Шаг 1 — получаем имя
@dp.message(Onboarding.name)
async def onboarding_name(msg: Message, state: FSMContext):
    name = (msg.text or "").strip()
    if not name:
        await msg.answer("Напиши, пожалуйста, как к тебе обращаться.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET name=$1, onboarding_step=1 WHERE id=$2",
            name, msg.from_user.id
        )

    # Кнопка для отправки контакта (request_contact работает с ReplyKeyboardButton)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await msg.answer(f"Отлично, {name}!\nТеперь отправь свой номер телефона.", reply_markup=kb)
    await state.set_state(Onboarding.phone)


# Шаг 2 — получаем телефон через контакт
@dp.message(Onboarding.phone)
async def onboarding_phone(msg: Message, state: FSMContext):
    # Проверяем, пришёл ли контакт (Telegram)
    if not msg.contact or not msg.contact.phone_number:
        await msg.answer("Нажми кнопку и пришли контакт (кнопка сверху).")
        return

    phone = msg.contact.phone_number

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET phone=$1, onboarding_step=2 WHERE id=$2",
            phone, msg.from_user.id
        )

    await msg.answer(
        "Последний вопрос:\nСколько денег у тебя сейчас в распоряжении?\n"
        "(например: 500000)"
    )
    await state.set_state(Onboarding.balance)


# Шаг 3 — стартовый капитал
@dp.message(Onboarding.balance)
async def onboarding_balance(msg: Message, state: FSMContext):
    text = (msg.text or "").replace(" ", "")
    try:
        balance_val = float(text)
    except Exception:
        await msg.answer("Введите число, например: 500000")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance=$1, onboarding_step=3 WHERE id=$2",
            balance_val, msg.from_user.id
        )

    await state.clear()

    await msg.answer(f"Принято! Записал {int(balance_val):,} UZS как стартовый капитал 💼".replace(",", " "))
    await msg.answer(
        "🎙 Как отправлять голосовые сообщения:\n"
        "1) Нажми и удерживай кнопку микрофона\n"
        "2) Скажи расход: «Кофе пятнадцать тысяч» или «Такси 120000»\n"
        "3) Отпусти для отправки\n\nПопробуй сейчас — отправь любой расход 👇"
    )


# -------------------- STATISTICS TEXT --------------------
@dp.message(Command("stat"))
async def stat(msg: Message):
    lang = await get_lang(msg.from_user.id)
    t, w, m = await get_stats(msg.from_user.id)

    text = (
        f"{LANG[lang]['stat_title']}\n\n"
        f"{LANG[lang]['today']}: <b>{int(t):,} UZS</b>\n"
        f"{LANG[lang]['week']}: <b>{int(w):,} UZS</b>\n"
        f"{LANG[lang]['month']}: <b>{int(m):,} UZS</b>\n"
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
        # берём стартовый баланс из users и суммируем расходы
        start_balance = await conn.fetchval("SELECT COALESCE(balance,0) FROM users WHERE id=$1", msg.from_user.id)
        total_spent = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_uzs), 0) FROM transactions WHERE user_id = $1",
            msg.from_user.id,
        )

    current = float(start_balance) - float(total_spent)

    text = (
        f"{LANG[lang]['balance_title']}:\n"
        f"{int(current):,} UZS"
    ).replace(",", " ")

    # Респонсивная inline-кнопка для истории
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


async def send_history(user_id: int, target_message):
    lang = await get_lang(user_id)
    rows = await get_last_transactions(user_id)

    if not rows:
        await target_message.answer(LANG[lang]["history_empty"])
        return

    lines = [LANG[lang]["history_title"]]
    for row in rows:
        title = row["title"] or ""
        category_key = row["category"]
        # переводим ключ категории в метку на нужном языке
        category_label = CATEGORY_LABELS.get(category_key, CATEGORY_LABELS["other"])[lang]
        amount = int(row["amount_uzs"])
        dt: datetime = row["created_at"]
        date_str = dt.strftime("%Y-%m-%d")

        line = f"{date_str} · {category_label} — {amount:,} UZS"
        lines.append(line.replace(",", " "))

    await target_message.answer("\n".join(lines))


# -------------------- ADD EXPENSE --------------------
@dp.message(F.text)
async def exp(msg: Message):
    # Пропускаем обработку системных команд
    if msg.text and msg.text.startswith("/"):
        return

    parsed = parse_expense(msg.text or "")
    if not parsed:
        # используем язык пользователя для сообщения об ошибке
        lang = await get_lang(msg.from_user.id)
        await msg.answer(LANG[lang]["bad_amount"])
        return

    # parse_expense возвращает: title, amount, category_key, lang_detected
    title, amt, category_key, lang_detected = parsed

    # но для отображения используем выбранный пользователем язык из БД
    user_lang = await get_lang(msg.from_user.id)
    category_label = CATEGORY_LABELS.get(category_key, CATEGORY_LABELS["other"])[user_lang]

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, title, category, amount_uzs)
            VALUES ($1,$2,$3,$4)
        """, msg.from_user.id, title, category_key, amt)

        # Обновляем баланс в users (вариант A: храним текущий баланс)
        # Баланс в users хранится как стартовый капитал, поэтому уменьшаем его
        await conn.execute(
            "UPDATE users SET balance = COALESCE(balance,0) - $1 WHERE id=$2",
            amt, msg.from_user.id
        )

    # Формируем сообщение на языке пользователя
    text_map = {
        "ru": f"🛡 Расход записан\n{category_label} — <b>{amt:,} UZS</b>",
        "uz": f"🛡 Xarajat yozildi\n{category_label} — <b>{amt:,} UZS</b>",
        "en": f"🛡 Expense recorded\n{category_label} — <b>{amt:,} UZS</b>",
    }
    msg_text = text_map.get(user_lang, text_map["uz"]).replace(",", " ")
    await msg.answer(msg_text)


# -------------------- MAIN --------------------
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
