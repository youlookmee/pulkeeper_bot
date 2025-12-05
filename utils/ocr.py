# utils/ocr.py
from openai import OpenAI
import base64
import json
import os
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_from_image(image_bytes: bytes):
    """
    OCR через GPT-4o mini Vision.
    Возвращает JSON:
    {
      "amount": float,
      "category": str,
      "description": str,
      "date": str
    }
    """

    encoded = base64.b64encode(image_bytes).decode("utf-8")

    system_prompt = """
Ты — OCR ассистент, который читает финансовые чеки (UZCARD/HUMO/терминал).
Верни строго JSON:

{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}

Правила:
- amount = самое крупное число (формат 5 000 000, 7000000, 5.000.000)
- category = одна из категорий: еда, развлечения, покупки, транспорт, прочее, другое
- description = краткое описание платежа
- date = DD.MM.YYYY или YYYY-MM-DD, или ""
Без пояснений, без текста вне JSON.
"""

    # ВАЖНО: правильный формат передачи картинки!
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Извлеки данные с чека"},
                    {
                        "type": "input_image",
                        "image": {
                            "data": encoded,
                            "media_type": "image/jpeg"
                        }
                    }
                ]
            }
        ]
    )

    raw = response.choices[0].message.content
    print("\n--- GPT OCR RAW ---\n", raw, "\n-------------------\n")

    # Ищем JSON
    try:
        json_text = re.search(r"\{[\s\S]*\}", raw).group(0)
        data = json.loads(json_text)
    except Exception as e:
        print("OCR JSON ERROR:", e)
        return None

    # Поправляем amount, если GPT ошибся
    if not data.get("amount") or float(data["amount"]) <= 0:
        numbers = re.findall(r"\d[\d\s,.]*", raw)
        if numbers:
            cleaned = [
                float(n.replace(" ", "").replace(",", "").replace(".", ""))
                for n in numbers
            ]
            data["amount"] = max(cleaned)

    return {
        "amount": float(data.get("amount", 0)),
        "category": data.get("category", "прочее"),
        "description": data.get("description", ""),
        "date": data.get("date", "")
    }
