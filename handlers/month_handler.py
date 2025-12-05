from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import extract

from services.db import SessionLocal, Transaction
from utils.format import fmt


async def month_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    session = SessionLocal()

    try:
        # Фильтруем транзакции за текущий месяц
        month = update.effective_message.date.month
        year = update.effective_message.date.year

        tx = (
            session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                extract("month", Transaction.tx_date) == month,
                extract("year", Transaction.tx_date) == year,
            )
            .all()
        )

        if not tx:
            await update.message.reply_text("❗ В этом месяце пока нет транзакций.")
            return

        income = sum(t.amount for t in tx if t.t_type == "income")
        expense = sum(t.amount for t in tx if t.t_type == "expense")

        balance = income - expense

        text = (
            f"📅 <b>Отчёт за месяц</b>\n"
            f"———————————————\n"
            f"Доходы: <b>{fmt(income)}</b>\n"
            f"Расходы: <b>{fmt(expense)}</b>\n"
            f"Чистый баланс: <b>{fmt(balance)}</b>\n"
            f"Транзакций: {len(tx)}"
        )

        await update.message.reply_text(text, parse_mode="HTML")

    finally:
        session.close()


# Handler
month_handler = CommandHandler("month", month_report)
