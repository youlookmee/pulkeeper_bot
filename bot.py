#!/usr/bin/env python3
import logging

from telegram.ext import ApplicationBuilder

from config import TELEGRAM_TOKEN

# Handlers
from handlers.start_handler import start_handler
from handlers.calc_handler import calc_conv_handler
from handlers.voice_handler import voice_handler

# Хендлеры транзакций (будут добавлены позже)
try:
    from handlers.transaction_handler import add_tx_handler, auto_tx_handler
except ImportError:
    add_tx_handler = None
    auto_tx_handler = None

# DB init
from services.db import init_db


# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting FinBot...")

    # ---------------------------------------------------
    # 📌 ИНИЦИАЛИЗАЦИЯ БАЗЫ (создаёт таблицы один раз)
    # ---------------------------------------------------
    init_db()
    logger.info("Database initialized.")

    # ---------------------------------------------------
    # 📌 Создаём приложение Telegram
    # ---------------------------------------------------
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ---------------------------------------------------
    # 📌 РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
    # ---------------------------------------------------

    # Старт
    app.add_handler(start_handler)

    # Финансовый калькулятор
    app.add_handler(calc_conv_handler)

    # Голосовые сообщения
    app.add_handler(voice_handler)

    # Транзакции — если хендлеры уже добавлены
    if add_tx_handler:
        app.add_handler(add_tx_handler)
    if auto_tx_handler:
        app.add_handler(auto_tx_handler)

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
