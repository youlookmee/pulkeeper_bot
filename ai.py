import os
import aiohttp
import json
from utils_number import normalize_text_to_number


# ============================================================
#                         API KEYS
# ============================================================
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


# ============================================================
#                1) DOWNLOAD VOICE FILE
# ============================================================
async def download_voice(bot, file_id: str, dest: str) -> str:
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, dest)
    return dest


# ============================================================
#                2) WHISPER → TEXT
# ============================================================
async def transcribe_voice(file_path: str) -> str | None:
    """
    Отправляет файл в OpenAI Whisper и получает текст.
    Возвращает None если ошибка.
    """

    headers = {"Authorization": f"Bearer {WHISPER_API_KEY}"}

    data = aiohttp.FormData()
    data.add_field("model", "whisper-1")
    data.add_field("file", open(file_path, "rb"), filename="voice.ogg")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WHISPER_URL, headers=headers, data=data) as resp:
                result = await resp.json()

                if "text" in result:
                    return result["text"]

                print("❗ Whisper error:", result)
                return None

    except Exception as e:
        print("❗ Whisper exception:", e)
        return None


# ============================================================
#               3) DEEPSEEK MESSAGE ANALYSIS
# ============================================================
async def analyze_message(text: str):
    """
    Анализ текста/голоса через DeepSeek.
    Возвращает строго:
    {
        "title": "...",
        "amount": число,
        "category": "food/transport/other/income",
        "is_income": true/false
    }
    """

    prompt = f"""
Ты финансовый ИИ.
Разбери текст и верни СТРОГО JSON:

{{
  "title": "...",
  "amount": "...",
  "category": "...",
  "is_income": true/false
}}

Считай ДОХОД:
"плюс", "+", "получил", "зарплата", "зп", "oylik", "keldi", "kelib tushdi"

Считай РАСХОД:
"минус", "-", "потратил", "расход", "такси", "еда", "кафе", "chiqim", "avoqat"

Сумму верни так, как видишь в тексте
(даже если это "1 млн", "1.2 mln", "bir million").

Текст: "{text}"
Ответь только JSON без лишнего текста.
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "deepseek-chat",
        "temperature": 0.1,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPSEEK_URL, headers=headers, json=body) as resp:
            data = await resp.json()

            # -----------------------------------------
            # ЛОГИРОВАНИЕ ОТВЕТА ДЛЯ ДЕБАГА
            # -----------------------------------------
            try:
                with open("ai_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"\n--- TIME {text} ---\n")
                    f.write(json.dumps(data, ensure_ascii=False, indent=2))
                    f.write("\n----------------------------------\n")
            except:
                pass

            # -----------------------------------------
            # ПАРСИНГ ОТВЕТА 
            # -----------------------------------------
            try:
                raw = data["choices"][0]["message"]["content"]

                # убираем ```json ... ```
                cleaned = (
                    raw.replace("```json", "")
                       .replace("```", "")
                       .replace("\n", " ")
                       .strip()
                )

                result = json.loads(cleaned)

            except Exception as e:
                print("❗ ERROR PARSING AI JSON:", e, "RAW:", data)
                return None

            # -----------------------------------------
            # НОРМАЛИЗАЦИЯ СУММЫ
            # -----------------------------------------
            amount_raw = str(result.get("amount", "0"))
            final_amount = normalize_text_to_number(amount_raw)

            result["amount"] = final_amount or 0

            return result
