import os
from telegram.ext import MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from services.whisper_service import transcribe_voice

# Папка для временных файлов
TEMP_DIR = "data/temp"

# Создаём папку, если её нет
os.makedirs(TEMP_DIR, exist_ok=True)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений от пользователя."""

    try:
        # Скачиваем файл OGG в temp
        file = await update.message.voice.get_file()
        file_path = os.path.join(TEMP_DIR, "voice.ogg")
        await file.download_to_drive(file_path)

        # Распознаём через Whisper
        text = transcribe_voice(file_path)

        # Отправляем результат пользователю
        await update.message.reply_text(f"🗣 Распознал голос:\n\n{text}")

        # Можно сохранить в context.user_data для дальнейшего шага диалога

    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке аудио: {e}")


# Handler для регистрации в bot.py
voice_handler = MessageHandler(filters.VOICE, handle_voice)
