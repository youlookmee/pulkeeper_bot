# handlers/chart_handler.py
import io
import matplotlib.pyplot as plt
from telegram import InputFile
from telegram.ext import CommandHandler
from db import get_session, Transaction
from datetime import datetime


async def chart_handler(update, context):
    user_id = update.message.from_user.id
    session = get_session()

    # Берём текущий месяц
    now = datetime.now()
    year, month = now.year, now.month

    # Достаём транзакции за месяц
    txs = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.tx_date >= datetime(year, month, 1)
    ).all()

    session.close()

    if not txs:
        await update.message.reply_text("📭 Нет данных за этот месяц.")
        return

    # Готовим данные
    days = []
    incomes = []
    expenses = []

    for tx in txs:
        day = tx.tx_date.day
        amount = float(tx.amount)

        if tx.type == "income":
            incomes.append((day, amount))
        else:
            expenses.append((day, amount))

    # Сортируем по дню
    incomes.sort(key=lambda x: x[0])
    expenses.sort(key=lambda x: x[0])

    # Разворачиваем
    x_income = [d for d, _ in incomes]
    y_income = [a for _, a in incomes]

    x_exp = [d for d, _ in expenses]
    y_exp = [a for _, a in expenses]

    # Рисуем график
    plt.figure(figsize=(8, 4))
    plt.plot(x_income, y_income, label="Доходы", linewidth=2)
    plt.plot(x_exp, y_exp, label="Расходы", linewidth=2)
    plt.title("График доходов и расходов за месяц")
    plt.xlabel("День месяца")
    plt.ylabel("Сумма")
    plt.grid(True)
    plt.legend()

    # Сохраняем в память
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png")
    img_buf.seek(0)
    plt.close()

    # Отправляем
    await update.message.reply_photo(photo=InputFile(img_buf, filename="chart.png"))


def get_chart_handler():
    return CommandHandler("chart", chart_handler)
