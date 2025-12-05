from openai import OpenAI
import base64
import json
import os
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_from_image(image_bytes: bytes):
    """OCR через GPT-4o mini Vision"""

    # Кодируем чек
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    system_prompt = """
Ты — OCR ассистент. Извлеки данные из чека.
СТРОГО верни JSON:

{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}

Правила:
- Сумма: самое крупное число на чеке. Убрать пробелы, вернуть как число.
- Категория: одна из — еда, развлечения, покупки, транспорт, прочее, другое.
- Описание: коротко.
- Дата: найти формат DD.MM.YYYY, YYYY-MM-DD, DD-MM-YYYY.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Извлеки данные"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded}"
                    }
                ]
            }
        ]
    )

    raw = response.choices[0].message.content
    print("\n--- RAW OCR ---\n", raw, "\n--------------\n")

    # Ищем JSON
    try:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("JSON not found")

        data = json.loads(match.group(0))

    except Exception as e:
        print("OCR JSON ERROR:", e)
        return None

    # Донастройка суммы — иногда GPT пишет странно
    amount = data.get("amount")
    if not amount or float(amount) <= 0:
        nums = re.findall(r"\d[\d\s.,]*", raw)
        nums_clean = []
        for x in nums:
            nn = x.replace(" ", "").replace(",", "").replace(".", "")
            if nn.isdigit():
                nums_clean.append(int(nn))
        if nums_clean:
            data["amount"] = max(nums_clean)

    return {
        "amount": float(data.get("amount", 0)),
        "category": data.get("category", "прочее"),
        "description": data.get("description", ""),
        "date": data.get("date", "")
    }
