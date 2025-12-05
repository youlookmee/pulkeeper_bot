# handlers/chart_handler.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telegram.ext import CommandHandler
from io import BytesIO
from services.db import get_session, Transaction


# Премиум-цвета Tinkoff Black
COLORS = [
    "#FFD700",  # Золотой
    "#FFA500",  # Оранжевый мягкий
    "#FF6F61",  # Коралловый
    "#6B5B95",  # Тёмно-фиолетовый
    "#009B77",  # Тинькофф зелёный
    "#4B4B4B",  # Графит
]


def generate_chart(user_id):
    session = get_session()

    rows = (
        session.query(Transaction.category, Transaction.amount)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.type == "expense")
        .all()
    )
    session.close()

    if not rows:
        return None

    # Собираем суммы по категориям
    data = {}
    for cat, amount in rows:
        data[cat] = data.get(cat, 0) + amount

    labels = list(data.keys())
    values = list(data.values())

    # --- TINKOFF BLACK BACKGROUND ---
    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(7, 6), dpi=140)
    fig.patch.set_facecolor("#000000")          # фон вокруг
    ax.set_facecolor("#000000")                 # фон диаграммы

    wedges, texts, autotexts = ax.pie(
        values,
        autopct="%1.1f%%",
        startangle=140,
        colors=COLORS[:len(values)],
        textprops={"color": "white", "weight": "bold", "fontsize": 12},
        wedgeprops={"linewidth": 1, "edgecolor": "#000000"}
    )

    # 🔥 Сделаем подписи крупнее и стильнее
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(12)
        autotext.set_weight("bold")

    # --- ЛЕГЕНДА ---
    ax.legend(
        wedges,
        labels,
        title="Категории",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=12,
        title_fontsize=12,
        facecolor="#111111",
        edgecolor="#333333"
    )

    # --- Заголовок ---
    ax.set_title(
        "💳 Tinkoff Black — расходы по категориям",
        fontsize=18,
        weight="bold",
        color="white",
        pad=20
    )

    # --- Сохранение картинки ---
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format="png", bbox_inches="tight", facecolor="#000000")
    img_bytes.seek(0)
    plt.close()

    return img_bytes


async def chart_command(update, context):
    user_id = update.effective_user.id
    img = generate_chart(user_id)

    if img is None:
        await update.message.reply_text("😕 Нет данных для диаграммы.")
        return

    await update.message.reply_photo(img)


def get_chart_handler():
    return CommandHandler("chart", chart_command)
