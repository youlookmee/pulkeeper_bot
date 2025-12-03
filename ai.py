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
    Возвращает JSON:
    {
        "title": "...",
        "amount": 15000,
        "category": "transport",
        "is_income": true/false
    }
    """

    prompt = f"""
Ты финансовый ИИ.
Разбери текст и верни СТРОГО JSON.

Найди:
- сумму
- доход или расход
- краткое название
- категорию

Считай ДОХОД, если слова:
"получил", "зарплата", "зп", "плюс", "+", "добавь", "kelib tushdi", "keldi", "oylik", "maosh"

Считай РАСХОД, если слова:
"потратил", "минус", "расход", "такси", "еда", "кафе", "avoqat", "chiqim"

Формат ответа строго:
{
  "title": "...",
  "amount": "...",
  "category": "...",
  "is_income": true/false
}

Текст пользователя: "{text}"
Ответь только JSON.
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

                # убираем ```json ```
                content = content.replace("```json", "").replace("```", "").strip()

                result = json.loads(content)

                # 🔥 НОРМАЛИЗАТОР СУММЫ
                # Превращает:
                # "1 млн" → 1000000
                # "30 тыс" → 30000
                # "1.5 mln" → 1500000
                # "1 200 500" → 1200500
                clean_amount = normalize_text_to_number(str(result["amount"]))

                result["amount"] = clean_amount if clean_amount is not None else 0

                return result

            except Exception as e:
                print("DeepSeek parse error:", e, "RAW:", data)
                return None
