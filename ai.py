import os
import aiohttp
import json

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


async def analyze_message(text: str):
    """
    Анализ текста через DeepSeek.
    Возвращает:
    {
      "title": "транспорт",
      "amount": 15000,
      "category": "transport",
      "is_income": false
    }
    """

    prompt = f"""
Ты — финансовый ассистент. Твоя задача — разобрать пользовательский текст
и вернуть строго JSON (без текста вокруг!). 

Правила:
1. Найди сумму. Примеры:
   "20k" → 20000, "15 000" → 15000, "10тыс" → 10000.
2. Определи title — название расхода/дохода.
3. Определи category из списка:
   - transport
   - food
   - fun
   - home
   - health
   - income
   - other
4. Определи is_income:
   true  — если это доход ("получил", "заработал", "пришло", "+500000")
   false — если расход ("потратил", "купил", "такси", "еда")

ВЕРНИ ТОЛЬКО JSON!

ПРИМЕР:
{{
  "title": "такси",
  "amount": 18000,
  "category": "transport",
  "is_income": false
}}

Текст пользователя: "{text}"
Ответ JSON:
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

                # Удаляем код-блоки DeepSeek
                content = content.replace("```json", "").replace("```", "").strip()

                return json.loads(content)

            except Exception as e:
                print("DeepSeek parse error:", e)
                print("RAW:", data)
                return None
