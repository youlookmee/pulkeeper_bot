import os
import aiohttp
import json

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


async def analyze_message(text: str):
    """
    Отправляет текст в DeepSeek и получает структуру:
      { "category": "...", "amount": 15000, "title": "такси" }
    """

    prompt = f"""
Ты — финансовый ассистент. 
Разбери текст расхода и верни строго JSON формата:

{{
  "title": "<название>",
  "amount": <число>,
  "category": "<одна категория: transport, food, fun, other>"
}}

Текст: "{text}"
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
                parsed = json.loads(content)
                return parsed
            except Exception as e:
                print("DeepSeek parse error:", e, data)
                return None
