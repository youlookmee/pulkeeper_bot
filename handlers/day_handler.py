# handlers/day_handler.py
from telegram.ext import CommandHandler
from services.db import get_session, Transaction
from datetime import datetime


async def day_report(update, context):
    session = get_session()
    user_id = update.message.from_user.id

    today = datetime.now().date()

    tx_list = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.tx_date == today
    ).all()

    session.close()

    if not tx_list:
        await update.message.reply_text("Сегодня ты ещё ничего не записал 😌")
        return

    income = sum(t.amount for t in tx_list if t.type == "income")
    expense = sum(t.amount for t in tx_list if t.type == "expense")
    balance = income - expense

    msg = (
        "📅 Отчёт за сегодня\n\n"
        f"Доходы: {income:,}\n"
        f"Расходы: {expense:,}\n"
        f"Баланс: {balance:,}\n\n"
        f"Транзакций: {len(tx_list)}"
    )

    await update.message.reply_text(msg)


day_handler = CommandHandler("day", day_report)
