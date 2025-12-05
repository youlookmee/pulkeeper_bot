#!/usr/bin/env python3
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import TELEGRAM_TOKEN

# ---- Handlers ----
from handlers.transaction_handler import transaction_handler
from handlers.report_handler import report_handler
from handlers.month_handler import month_handler
from handlers.day_handler import day_handler
from handlers.chart_handler import get_chart_handler
from handlers.history_handler import history_handler
from handlers.photo_handler import photo_handler
from handlers.receipt_handler import receipt_callback

# ---- DB ----
from services.db import init_db


# ---- Логи ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- /start ----
async def start(update, context):
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я финансовый ассистент. Можешь просто написать сумму и описание:\n"
        "Например:\n"
        "• 20000 ужин\n"
        "• 50000 такси\n"
        "• 1.5 млн зарплата\n\n"
        "И я всё сохраню автоматически! 💰\n\n"
        "Также я умею читать фото чеков 📸"
    )


# ---- Главная функция ----
def main():
    logger.info("Starting bot...")

    # Инициализация БД
    init_db()
    logger.info("Database initialized")

    # Telegram application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ---- Команды ----
    app.add_handler(CommandHandler("start", start))
    app.add_handler(report_handler)
    app.add_handler(month_handler)
    app.add_handler(day_handler)
    app.add_handler(history_handler())
    app.add_handler(get_chart_handler())

    # ---- Фото чеков ----
    app.add_handler(photo_handler)

    # ---- Подтверждение Одобрить / Отклонить ----
    app.add_handler(CallbackQueryHandler(receipt_callback))

    # ---- Авто-парсинг текста транзакций ----
    app.add_handler(transaction_handler)

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
