# report_handler.py
from telegram.ext import CommandHandler
from services.db import get_session, Transaction
from sqlalchemy import func, desc

# Форматирование числа с разделителями
def fmt_amount(value):
    try:
        # value может быть Decimal, float или None
        if value is None:
            return "0"
        v = float(value)
        # Если есть дробная часть — покажем две цифры, иначе целое
        if abs(v - int(v)) >= 0.01:
            return f"{v:,.2f}"
        return f"{int(v):,}"
    except Exception:
        return str(value)


def compute_report_for_user(user_id):
    """
    Возвращает словарь с вычисленными полями:
    {
      total_income, total_expense, balance, tx_count, top_categories: [(cat, sum), ...]
    }
    """
    session = get_session()
    try:
        # Сумма доходов
        total_income = session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "income"
        ).scalar() or 0

        # Сумма расходов
        total_expense = session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense"
        ).scalar() or 0

        # Кол-во транзакций всего
        tx_count = session.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id
        ).scalar() or 0

        # Топ категорий по расходам (category, sum)
        top_q = session.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense"
        ).group_by(Transaction.category).order_by(desc("total")).limit(5)

        top_categories = [(row.category or "прочее", row.total) for row in top_q]

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": (total_income - total_expense),
            "tx_count": tx_count,
            "top_categories": top_categories
        }
    finally:
        session.close()


# ---------- Command handler ----------
async def command_report(update, context):
    user_id = update.effective_user.id

    await update.message.reply_text("Считаю отчёт... ⏳")

    data = compute_report_for_user(user_id)

    income = fmt_amount(data["total_income"])
    expense = fmt_amount(data["total_expense"])
    balance = fmt_amount(data["balance"])
    tx_count = int(data["tx_count"])

    # Формируем текст отчёта
    text_lines = [
        "📊 Полный отчёт",
        "----------------------------",
        f"Всего транзакций: {tx_count}",
        f"Доходы: {income}",
        f"Расходы: {expense}",
        f"Чистый баланс: {balance}",
        "----------------------------",
    ]

    if data["top_categories"]:
        text_lines.append("Топ-категории расходов:")
        for idx, (cat, total) in enumerate(data["top_categories"], start=1):
            text_lines.append(f"{idx}. {cat} — {fmt_amount(total)}")
    else:
        text_lines.append("Топ-категорий расходов нет.")

    text = "\n".join(text_lines)

    await update.message.reply_text(text)


report_handler = CommandHandler("report", command_report)
