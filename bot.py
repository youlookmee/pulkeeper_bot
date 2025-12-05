#!/usr/bin/env python3
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)

from config import TELEGRAM_TOKEN

# ---- Handlers ----
from handlers.transaction_handler import transaction_handler      # авто-запись суммы
from handlers.report_handler import report_handler                # /report
from handlers.month_handler import month_handler                  # /month
from handlers.day_handler import day_handler
from handlers.chart_handler import get_chart_handler


# (дальше добавим /day, /chart, AI и др.)

# ---- DB ----
from services.db import init_db


# ---- Логи ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- Команда /start ----
async def start(update, context):
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я финансовый ассистент. Можешь просто написать сумму и описание:\n"
        "Например:\n"
        "• 20000 ужин\n"
        "• 50000 такси\n"
        "• 1.5 млн зарплата\n\n"
        "И я всё сохраню автоматически! 💰"
    )


# ---- Главная функция ----
def main():
    logger.info("Starting bot...")

    # Инициализация БД (создаёт таблицы при запуске)
    init_db()
    logger.info("Database initialized")

    # Создаём приложение Telegram
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ---- Регистрируем хендлеры ----
    app.add_handler(CommandHandler("start", start))     # /start
    app.add_handler(report_handler)                     # /report
    app.add_handler(month_handler)                      # /month
    app.add_handler(day_handler)
    app.add_handler(transaction_handler)                # авто-парсер суммы
    app.add_handler(get_chart_handler())

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
