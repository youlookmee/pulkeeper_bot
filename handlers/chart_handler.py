# handlers/chart_handler.py
import matplotlib
matplotlib.use("Agg")  # важно для сервера
import matplotlib.pyplot as plt

from telegram.ext import CommandHandler
from io import BytesIO
from services.db import get_session, Transaction


# 🎨 красивые цвета (плавные пастельные)
COLORS = [
    "#FF6F61", "#6B5B95", "#88B04B", "#F7CAC9", "#92A8D1",
    "#955251", "#B565A7", "#009B77", "#DD4124", "#45B8AC"
]


# ======== Генерация диаграммы ========
def generate_chart(user_id):
    session = get_session()

    # Собираем категории и суммы
    rows = (
        session.query(Transaction.category, Transaction.amount)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.type == "expense")  # только расходы
        .all()
    )
    session.close()

    if not rows:
        return None  # показать сообщение, что данных нет

    # Группируем суммы по категориям
    data = {}
    for cat, amount in rows:
        data[cat] = data.get(cat, 0) + amount

    labels = list(data.keys())
    values = list(data.values())

    # Создаем красивую диаграмму
    fig, ax = plt.subplots(figsize=(6, 6), dpi=120)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        colors=COLORS[:len(values)],
        textprops={"color": "white", "weight": "bold"},
    )

    # Стиль подписи процентов
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_weight("bold")

    ax.set_title("📊 Расходы по категориям", fontsize=16, weight="bold")

    # сохраняем в память
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format="png", transparent=False, bbox_inches="tight")
    img_bytes.seek(0)
    plt.close()

    return img_bytes


# ======== Хендлер /chart ========
async def chart_command(update, context):
    user_id = update.effective_user.id

    img = generate_chart(user_id)

    if img is None:
        await update.message.reply_text("😕 У тебя пока нет расходов для построения диаграммы.")
        return

    await update.message.reply_photo(img)


# экспортируем handler
def get_chart_handler():
    return CommandHandler("chart", chart_command)
