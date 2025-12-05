# handlers/transaction_handler.py
from telegram.ext import MessageHandler, filters
from parser import parse_transaction
from services.db import get_session, Transaction


# 1) Функция сохранения
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


# 2) Логика / авто парсинг сообщений
async def handle_transaction(update, context):
    text = update.message.text
    user_id = update.message.from_user.id

    data = parse_transaction(text)
    if not data:
        return

    save_transaction(user_id, data)

    await update.message.reply_text(
        f"🟢 Записал!\n"
        f"Сумма: {data['amount']}\n"
        f"Категория: {data['category']}\n"
        f"Тип: {data['type']}"
    )


# 3) Handler
transaction_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    handle_transaction
)
