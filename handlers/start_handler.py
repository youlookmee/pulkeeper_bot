from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋\n"
        "Я финансовый ассистент. Могу рассчитать твое финансовое состояние.\n\n"
        "Для начала анализа нажми команду:\n"
        "/calculate"
    )

start_handler = CommandHandler("start", start)
