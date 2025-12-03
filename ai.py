import os
import aiohttp
import json
from utils_number import normalize_text_to_number

WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


async def download_voice(bot, file_id: str, dest: str) -> str:
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, dest)
    return dest


async def transcribe_voice(file_path: str) -> str | None:
    headers = {"Authorization": f"Bearer {WHISPER_API_KEY}"}

    data = aiohttp.FormData()
    data.add_field("model", "whisper-1")
    data.add_field("file", open(file_path, "rb"), filename="voice.ogg")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WHISPER_URL, headers=headers, data=data) as resp:
                result = await resp.json()
                return result.get("text")
    except Exception as e:
        print("Whisper exception:", e)
        return None


async def analyze_message(text: str):
    prompt = f"""
Ты финансовый ИИ. Разбери текст и верни строго JSON:
{{
  "title": "...",
  "amount": "...",
  "category": "...",
  "is_income": true/false
}}

Доход = если слова: плюс, +, получил, зарплата, oylik, kelib tushdi, keldi  
Расход = если слова: минус, -, потратил, расход, такси, еда, chiqim, avoqat  

Текст: "{text}"
Ответь только JSON.
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

    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPSEEK_URL, headers=headers, json=body) as resp:
            data = await resp.json()

            try:
                content = data["choices"][0]["message"]["content"]
                content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(content)

                # 🔥 нормализуем сумму
                amount_raw = str(result.get("amount", "0"))
                amount_clean = normalize_text_to_number(amount_raw)

                result["amount"] = amount_clean or 0
                return result

            except Exception as e:
                print("DeepSeek parse error:", e, "RAW:", data)
                return None
