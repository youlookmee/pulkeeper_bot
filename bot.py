import logging
from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_TOKEN
from services.db import init_db
from handlers.photo_handler import photo_handler
from handlers.receipt_handler import receipt_callback_handler, receipt_edit_handler  # note: function and handler factory
from handlers.transaction_handler import transaction_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text("Привет! Отправь фото чека или напиши сумму + описание.")

def main():
    logger.info("Starting bot...")
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(photo_handler)
    app.add_handler(receipt_callback_handler())  # callback handler
    app.add_handler(transaction_handler)

    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
