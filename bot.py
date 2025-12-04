#!/usr/bin/env python3
import logging

from telegram.ext import (
    ApplicationBuilder,
)

from config import TELEGRAM_TOKEN

# Handlers
from handlers.start_handler import start_handler
from handlers.calc_handler import calc_conv_handler
from handlers.voice_handler import voice_handler

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting FinBot...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ➤ Регистрируем handlers
    app.add_handler(start_handler)       # /start
    app.add_handler(calc_conv_handler)   # /calculate (диалог)
    app.add_handler(voice_handler)       # голосовые сообщения

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
