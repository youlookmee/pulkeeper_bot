import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Telegram бот
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# Whisper API (OpenAI)
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

# ❗ Вот это должно быть обязательно
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка
if not TELEGRAM_TOKEN:
    raise ValueError("Ошибка: TELEGRAM_TOKEN отсутствует в .env")

if not DEEPSEEK_API_KEY:
    print("⚠️ Внимание: DEEPSEEK_API_KEY отсутствует в .env")

if not WHISPER_API_KEY:
    print("⚠️ Whisper не будет работать: WHISPER_API_KEY отсутствует в .env")
