# finbot/handlers/transaction_handler.py
from telegram.ext import MessageHandler, CommandHandler, filters
from utils.parser import parse_transaction
from services.db import get_session
from models import Transaction


async def add_transaction_to_db(user_id: int, data: dict):
    session = get_session()

    tx = Transaction(
        user_id=user_id,
        type=data["type"],
        amount=data["amount"],
        category=data["category"],
        description=data["description"],
        tx_date=data["date"]
    )

    session.add(tx)
    session.commit()
    session.close()


# ---------- Команда /add ----------
async def manual_add(update, context):
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("Использование: /add сумма описание\n\nПример:\n/add 12000 ужин")
        return

    parsed = parse_transaction(text)
    if not parsed:
        await update.message.reply_text("Не смог определить сумму. Попробуй другой формат.")
        return

    await add_transaction_to_db(update.effective_user.id, parsed)

    await update.message.reply_text(
        f"Добавлено ✔️\n"
        f"Сумма: {parsed['amount']}\n"
        f"Категория: {parsed['category']}\n"
        f"Тип: {parsed['type']}"
    )


add_tx_handler = CommandHandler("add", manual_add)


# ---------- Автоматический парсер всех сообщений ----------
async def auto_parse(update, context):
    text = update.message.text

    parsed = parse_transaction(text)
    if not parsed:
        return  # Просто обычное сообщение

    await add_transaction_to_db(update.effective_user.id, parsed)

    await update.message.reply_text(
        f"🟢 Записал операцию!\n"
        f"Сумма: {parsed['amount']}\n"
        f"Категория: {parsed['category']}\n"
        f"Тип: {parsed['type']}"
    )


auto_tx_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, auto_parse)
