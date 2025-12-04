import io
import os
import matplotlib.pyplot as plt
import pandas as pd

# Папка для временных файлов
TEMP_DIR = "data/temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_bar_chart(fin_data: dict) -> io.BytesIO:
    """
    Создаёт bar chart (график) по основным финансовым показателям.
    """

    keys = ["income", "expenses", "savings", "loans", "assets", "net_worth"]
    labels = ["Доход", "Расходы", "Накопления", "Кредиты", "Активы", "Net Worth"]
    values = [fin_data.get(k, 0) for k in keys]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values)
    ax.set_title("Финансовые показатели")
    ax.set_ylabel("Сумма")
    ax.set_xticklabels(labels, rotation=30)

    bio = io.BytesIO()
    plt.tight_layout()
    fig.savefig(bio, format="png")
    plt.close(fig)
    bio.seek(0)
    return bio


def generate_table_image(fin_data: dict) -> io.BytesIO:
    """
    Создаёт изображение таблицы в PNG формате из финансовых данных.
    """

    df = pd.DataFrame({
        "Показатель": [
            "Доход", "Расходы", "Накопления",
            "Кредиты", "Активы", "Net Worth",
            "Ежемесячный остаток",
            "Коэф. сбережений",
            "Долговая нагрузка",
            "Месяцев резерва",
            "Фин. балл"
        ],
        "Значение": [
            fin_data["income"],
            fin_data["expenses"],
            fin_data["savings"],
            fin_data["loans"],
            fin_data["assets"],
            fin_data["net_worth"],
            fin_data["monthly_surplus"],
            round(fin_data["saving_rate"], 3),
            round(fin_data["debt_ratio"], 3),
            fin_data["months_of_reserve"],
            fin_data["score"]
        ]
    })

    fig, ax = plt.subplots(figsize=(6, len(df) * 0.45))
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc="center",
        cellLoc="left"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.2)

    bio = io.BytesIO()
    plt.tight_layout()
    fig.savefig(bio, format="png")
    plt.close(fig)
    bio.seek(0)
    return bio
