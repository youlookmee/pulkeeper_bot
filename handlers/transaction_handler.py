# transaction_handler.py
from telegram.ext import CommandHandler, MessageHandler, filters
from parser import parse_transaction
from services.db import get_session, Transaction


# -------------------------------
# 1) Функция записи транзакции
# -------------------------------
def save_transaction(user_id: int, data: dict):
    session = get_session()

    tx = Transaction(
        user_id=user_id,
        type=data["type"],
        amount=data["amount"],
        category=data["category"],
        description=data["description"],
        tx_date=data["date"],
    )

    session.add(tx)
    session.commit()
    session.close()


# -------------------------------
# 2) Команда: /add 10000 кофе
# -------------------------------
async def command_add(update, context):
    if not context.args:
        await update.message.reply_text(
            "Использование:\n/add сумма описание\n\nПример:\n/add 20000 ужин"
        )
        return

    text = " ".join(context.args)
    parsed = parse_transaction(text)

    if not parsed:
        await update.message.reply_text("Не смог распознать сумму. Попробуй так:\n/add 20000 ужин")
        return

    save_transaction(update.effective_user.id, parsed)

    await update.message.reply_text(
        f"Добавлено ✔️\n"
        f"Сумма: {parsed['amount']}\n"
        f"Тип: {parsed['type']}\n"
        f"Категория: {parsed['category']}"
    )


add_tx_handler = CommandHandler("add", command_add)


# -------------------------------
# 3) Автопарсер текстовых сообщений
# -------------------------------
async def auto_parse(update, context):
    text = update.message.text
    parsed = parse_transaction(text)

    # Если не распознано — пропускаем
    if not parsed:
        return

    save_transaction(update.effective_user.id, parsed)

    await update.message.reply_text(
        f"🟢 Записал!\n"
        f"Сумма: {parsed['amount']}\n"
        f"Категория: {parsed['category']}\n"
        f"Тип: {parsed['type']}"
    )

from telegram.ext import MessageHandler, filters

# вот ЭТО и нужно экспортировать!
transaction_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, auto_tx_handler)
