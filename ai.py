import os
import aiohttp
import json

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

async def analyze_message(text: str):
    """
    Анализ расхода через DeepSeek.
    AI обязан вернуть чистый JSON вида:
    {
      "title": "такси",
      "amount": 15000,
      "category": "transport"
    }
    """

    prompt = f"""
Ты — финансовый ассистент. Разбери пользовательский текст и верни строго JSON (без пояснений).

Категории:
- transport
- food
- fun
- other

Инструкция:
1. Найди сумму (число). Если написано "20k" → 20000, "15 000" → 15000.
2. Найди название расхода.
3. Определи категорию.
4. Верни ТОЛЬКО JSON, без текста и без форматирования.

Пример правильного ответа:
{{
  "title": "такси",
  "amount": 20000,
  "category": "transport"
}}

Пользовательский текст: "{text}"
Ответи JSON:
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

                # иногда DeepSeek пишет ```json ... ```
                content = content.replace("```json", "").replace("```", "").strip()

                return json.loads(content)

            except Exception as e:
                print("DeepSeek parse error:", e, "RAW:", data)
                return None
