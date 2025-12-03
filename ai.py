import os
import aiohttp
import json

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


async def analyze_message(text: str):
    """
    Анализ текста: определение дохода или расхода.
    AI обязан вернуть строгий JSON:

    {
      "title": "текст",
      "amount": 15000,
      "category": "transport",
      "is_income": false
    }
    """

    prompt = f"""
Ты — финансовый ассистент. Разбери текст пользователя и верни СТРОГО JSON.

Категории для расхода:
- transport
- food
- fun
- other

Если это ДОХОД — категория должна быть "income", а поле is_income = true.

Правила:
1. Если фраза содержит: "зарплата", "получил", "пришло", "доход", "добавить сумму", "+100000" → это доход.
2. Если фраза содержит покупку — это расход.
3. Сумму всегда преобразуй в число: "20k" → 20000, "3 млн" → 3000000.
4. Верни ТОЛЬКО JSON.

ПРИМЕР ДОХОДА:
{{
  "title": "зарплата",
  "amount": 3000000,
  "category": "income",
  "is_income": true
}}

ПРИМЕР РАСХОДА:
{{
  "title": "такси",
  "amount": 20000,
  "category": "transport",
  "is_income": false
}}

ТЕКСТ ПОЛЬЗОВАТЕЛЯ: "{text}"
Ответи только JSON:
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

                # DeepSeek часто добавляет ```json
                content = content.replace("```json", "").replace("```", "").strip()

                return json.loads(content)

            except Exception as e:
                print("DeepSeek PARSE ERROR:", e, "RAW:", data)
                return None
