# utils/ocr.py
from openai import OpenAI
import base64
import json
import os
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_from_image(image_bytes: bytes):
    """
    Надёжный OCR через GPT-4o mini Vision.
    Возвращает:
    {
        "amount": float,
        "category": str,
        "description": str,
        "date": str
    }
    """

    # Кодируем картинку
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
Ты — профессиональный OCR ассистент для финансовых чеков (UZCARD/HUMO/терминал).
Твоя задача: извлечь точные данные о транзакции.

СТРОГО верни JSON ТОЛЬКО в таком формате:

{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}

ПРАВИЛА:

1) Сумма:
   - Ищи самое крупное число на чеке.
   - Учитывай возможные форматы: 
     "5 000 000", "7 000 000.00", "5000000", "5.000.000".
   - Верни число БЕЗ пробелов и знаков, как float или int.

2) Категория (выбери только 1):
   "еда", "развлечения", "покупки", "транспорт", "прочее", "другое".

3) Description:
   - кратко объясни платеж: "оплата", "пополнение", "перевод", "погашение долга", 
     или по смыслу текста.

4) Дата:
   - Найди дату в форматах: DD.MM.YYYY, YYYY-MM-DD, DD-MM-YYYY.
   - Если даты нет — верни "".

ВАЖНО:
— Не добавляй никаких комментариев.
— Только чистый JSON без текста вокруг.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Извлеки данные с этого чека"},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{encoded}"}
                ]
            }
        ]
    )

    raw = response.choices[0].message.content
    print("\n--- GPT RAW OCR ---\n", raw, "\n-------------------\n")

    # Безопасно ищем JSON
    try:
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            raise ValueError("JSON not found")

        data = json.loads(json_match.group(0))

    except Exception as e:
        print("OCR JSON ERROR:", e)
        return None

    # Автодоп. проверка суммы
    if not data.get("amount") or float(data["amount"]) <= 0:
        numbers = re.findall(r"\d[\d\s,.]*", raw)
        cleaned = []
        for n in numbers:
            nn = float(n.replace(" ", "").replace(",", "").replace(".", ""))
            cleaned.append(nn)
        if cleaned:
            data["amount"] = max(cleaned)

    return {
        "amount": float(data.get("amount", 0)),
        "category": data.get("category", "прочее"),
        "description": data.get("description", ""),
        "date": data.get("date", "")
    }
