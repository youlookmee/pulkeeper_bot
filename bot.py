#!/usr/bin/env python3
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import TELEGRAM_TOKEN

# Handlers
from handlers import transaction_handler
from handlers.report_handler import report_handler
from handlers.month_handler import month_handler

# DB
from services.db import init_db

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update, context):
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я финансовый ассистент. Можешь просто написать сумму и описание:\n"
        "Например:\n"
        "  20000 ужин\n"
        "  50000 такси\n"
        "  1.5 млн зарплата\n\n"
        "И я всё сохраню автоматически! 💰"
    )


def main():
    logger.info("Starting bot...")

    # --------------------------
    # Создаём таблицы в базе
    # --------------------------
    init_db()
    logger.info("Database initialized")

    # --------------------------
    # Создаём приложение Telegram
    # --------------------------
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # --------------------------
    # Handlers
    # --------------------------
    app.add_handler(CommandHandler("start", start))

    # Команда: /add 20000 кофе
    app.add_handler(add_tx_handler)

    app.add_handler(report_handler)
    app.add_handler(month_handler)


    # Автоматическое распознавание всех сообщений
    app.add_handler(auto_tx_handler)

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
