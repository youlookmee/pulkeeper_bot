import os
import aiohttp
import json
from utils_number import normalize_text_to_number

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


# ------------------ TRANSCRIBE AUDIO (WHISPER) ------------------
async def transcribe_voice(file_path: str) -> str | None:
    """Отправляет файл (ogg/mp3/webm/m4a) в Whisper и возвращает текст"""

    headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("file", f, filename=os.path.basename(file_path))
                form.add_field("model", "whisper-1")

                async with session.post(WHISPER_URL, headers=headers, data=form) as resp:
                    result = await resp.json()
                    return result.get("text")

    except Exception as e:
        print("Whisper error:", e)
        return None
        
# 1 — Whisper дал текст
text = transcript

# 2 — пробуем извлечь сумму сами (слова → число)
amount_from_words = normalize_text_to_number(text)

# 3 — если нашли сумму — отдаём напрямую в бот
if amount_from_words:
    return {
        "title": text,
        "amount": amount_from_words,
        "category": "other"
    }

# ------------------ ANALYZE TEXT (DEEPSEEK) ------------------
async def analyze_message(text: str):
    """Анализ расхода или дохода через DeepSeek. Возвращает JSON."""

    print("AI REQUEST:", text)

    prompt = f"""
Ты — финансовый ассистент. Разбери пользовательский текст и верни строго JSON без пояснений.

Определи:
- title — название  
- amount — сумма  
- category — категория (transport, food, fun, other)
- type — расход или доход: "expense" или "income"

Правила:
- Если есть + или слова типа "получил", "зарплата" → это доход.
- Если обычный текст → это расход.
- Верни только JSON.

Пользовательский текст: "{text}"
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPSEEK_URL, headers=headers, json=body) as resp:
            data = await resp.json()

            try:
                content = data["choices"][0]["message"]["content"]

                # DeepSeek иногда присылает в виде ```json
                content = content.replace("```json", "").replace("```", "").strip()

                parsed = json.loads(content)
                print("AI RESULT:", parsed)
                return parsed

            except Exception as e:
                print("DeepSeek parse error:", e, "RAW:", data)
                return None
