import os
import aiohttp
import json
import asyncio

from utils_number import normalize_text_to_number

# 🔑 API Keys
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")  # OpenAI / DeepSeek ключ
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 🌐 API URLs
WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


# ----------------------------------------------------------
# 1) Скачивание голосового сообщения
# ----------------------------------------------------------
async def download_voice(bot, file_id: str, dest: str) -> str:
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, dest)
    return dest


# ----------------------------------------------------------
# 2) Whisper → текст
# ----------------------------------------------------------
async def transcribe_voice(file_path: str) -> str | None:
    headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}"
    }

    data = aiohttp.FormData()
    data.add_field("model", "whisper-1")
    data.add_field("file", open(file_path, "rb"), filename="voice.ogg")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WHISPER_URL, headers=headers, data=data) as resp:
                result = await resp.json()

                if "text" in result:
                    return result["text"]

                print("Whisper error:", result)
                return None

    except Exception as e:
        print("Whisper exception:", e)
        return None


# ----------------------------------------------------------
# 3) DeepSeek — разбор текста
# ----------------------------------------------------------
async def analyze_message(text: str):
    """
    Анализ текста/голоса через DeepSeek.
    Возвращает JSON:
    {
        "title": "...",
        "amount": 15000,
        "category": "transport",
        "is_income": true/false
    }
    """

    prompt = f"""
Ты ИИ-помощник для финансов.
Разбери текст и верни строго JSON.

Определи:
- является ли операция доходом или расходом
- сумму
- название
- категорию

Правила:
1. ДОХОД, если встречаются слова:
   "получил", "зарплата", "зп", "плюс", "+", "добавь", "kelib tushdi", "keldi", "oylik", "maosh"

2. РАСХОД, если слова:
   "потратил", "минус", "расход", "такси", "еда", "кафе", "avoqat", "chiqim"

3. Верни JSON вида:
{
  "title": "...",
  "amount": ЧИСЛО,
  "category": "transport/food/other",
  "is_income": true/false
}

Текст пользователя: "{text}"
Ответь ТОЛЬКО JSON:
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPSEEK_URL, headers=headers, json=body) as resp:
            data = await resp.json()

            try:
                content = data["choices"][0]["message"]["content"]

                # очищаем JSON от ```json ```
                content = content.replace("```json", "").replace("```", "").strip()

                result = json.loads(content)

                # 🔥 НОРМАЛИЗАЦИЯ СУММЫ
                # Поддерживает: "1 млн", "30 тыс", "1.5 млн", "1 000 000"
                result["amount"] = normalize_text_to_number(str(result["amount"]))

                return result

            except Exception as e:
                print("DeepSeek parse error:", e, "RAW:", data)
                return None
