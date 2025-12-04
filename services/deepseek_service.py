import requests
from config import DEEPSEEK_API_KEY, MODEL_NAME
from prompts import FULL_PROMPT

API_URL = "https://api.deepseek.com/v1/chat/completions"

def generate_financial_advice(fin_data: dict) -> str:
    """
    Отправляет данные пользователя в DeepSeek и получает анализ + рекомендации.
    """

    # Финансовые данные превращаем в удобный текст
    snapshot = "\n".join([f"{k}: {v}" for k, v in fin_data.items()])

    prompt = f"{FULL_PROMPT}\n\nВот финансовые данные пользователя:\n{snapshot}\n\nСформируй аналитический отчёт."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()

        # Возвращаем текст ответа
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"Ошибка при работе с DeepSeek: {e}"
