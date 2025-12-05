# handlers/month_handler.py
from telegram.ext import CommandHandler
from services.db import get_session, Transaction


async def month_report(update, context):
    session = get_session()

    tx_list = session.query(Transaction).filter(
        Transaction.user_id == update.message.from_user.id
    ).all()

    session.close()

    if not tx_list:
        await update.message.reply_text("За месяц ничего нет.")
        return

    income = sum(t.amount for t in tx_list if t.type == "income")
    expense = sum(t.amount for t in tx_list if t.type == "expense")
    balance = income - expense

    msg = (
        "📅 Отчёт за месяц\n\n"
        f"Доходы: {income:,}\n"
        f"Расходы: {expense:,}\n"
        f"Баланс: {balance:,}"
    )

    await update.message.reply_text(msg)


month_handler = CommandHandler("month", month_report)
