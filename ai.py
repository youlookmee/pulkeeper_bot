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
# 3) DeepSeek — разбор текста (если Whisper дал текст)
# ----------------------------------------------------------
async def analyze_message(text: str) -> dict | None:
    """
    DeepSeek должен вернуть JSON:
    {
        "title": "...",
        "amount": 15000,
        "category": "transport"
    }
    """

    # 🔥 Сначала пробуем вытащить сумму без ИИ (узбекский/русский)
    quick = normalize_text_to_number(text)
    if quick:
        return {
            "title": text,
            "amount": quick,
            "category": "other"
        }

    # ❗ Если бот не понял сумму — подключаем DeepSeek
    prompt = f"""
Распознай финансовый запрос. Верни строго JSON:

Пример корректного JSON:
{{
  "title": "такси",
  "amount": 20000,
  "category": "transport"
}}

Категории:
- transport
- food
- fun
- other
- income

Важно:
• amount — только число
• никакого текста вне JSON

Текст пользователя: "{text}"
Верни только JSON:
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_URL, headers=headers, json=body) as resp:
                data = await resp.json()

                # print("RAW DeepSeek:", data)  # для дебага

                content = data["choices"][0]["message"]["content"]
                content = content.replace("```json", "").replace("```", "").strip()

                return json.loads(content)

    except Exception as e:
        print("DeepSeek parse error:", e)
        return None
