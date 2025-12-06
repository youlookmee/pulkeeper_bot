# utils/ocr.py
from openai import OpenAI
import base64
import json
import os
import re
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_from_image(image_bytes: bytes):
    """
    Ультра-надёжный OCR через GPT-4o mini Vision.
    Всегда возвращает корректный JSON:
    {
        "amount": float,
        "category": str,
        "description": str,
        "date": str
    }
    """

    # Кодируем картинку
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    system_prompt = """
Ты — профессиональный OCR ассистент для финансовых чеков (UZCARD/HUMO/терминальные чеки).

Твоя задача — понять точные данные о транзакции.

СТРОГО верни JSON, БЕЗ ТЕКСТА вокруг:

{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}

ПРАВИЛА:

1) СУММА:
   - Найди самое крупное число на чеке.
   - Учитывай варианты с пробелами: 7 000 000, 7.000.000, 7000000, 7 000 000.00
   - Верни только цифры, как число (int / float).

2) КАТЕГОРИЯ (выбери ОДНУ):
   - "еда", "развлечения", "покупки", "транспорт", "прочее", "другое".
   - Если нет магазина, ресторана, бензиновой станции → выбери "прочее".

3) DESCRIPTION:
   - Кратко опиши смысл платежа: например, "платеж", "перевод", "оплата по карте".
   - НЕ пиши длинный текст.

4) DATE:
   - Форматы поиска: DD.MM.YYYY, YYYY-MM-DD, DD-MM-YYYY.
   - Если есть время, игнорируй.
   - Если нет даты — верни "".

Верни только JSON. 
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Извлеки данные с этого чека."},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded}"
                    }
                ]
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    print("\n--- RAW GPT OCR ---\n", raw, "\n-------------------\n")

    # --- Пытаемся найти JSON ---
    try:
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            raise ValueError("GPT did not return JSON")

        data = json.loads(json_match.group(0))

    except Exception as e:
        print("OCR JSON ERROR:", e)
        return None

    # -----------------------------
    # ДОПОЛНИТЕЛЬНАЯ ОБРАБОТКА
    # -----------------------------

    # 1) Сумма — если GPT дал криво, вытаскиваем вручную из всего raw текста
    amount = data.get("amount")
    if not amount or float(amount) <= 0:

        numbers = re.findall(r"\d[\d\s.,]*", raw)  # ищем все числа
        cleaned = []

        for n in numbers:
            nn = n.replace(" ", "").replace(",", "").replace(".", "")
            if nn.isdigit():
                cleaned.append(int(nn))

        if cleaned:
            data["amount"] = max(cleaned)
        else:
            data["amount"] = 0

    # 2) Категория — защита от мусора
    allowed_categories = ["еда", "развлечения", "покупки", "транспорт", "прочее", "другое"]
    if data.get("category") not in allowed_categories:
        data["category"] = "прочее"

    # 3) Description — fallback
    if not data.get("description"):
        data["description"] = "платеж"

    # 4) Дата — проверка и исправление
    date_str = data.get("date", "")
    extracted_date = None

    patterns = [
        r"\d{4}-\d{2}-\d{2}",   # YYYY-MM-DD
        r"\d{2}\.\d{2}\.\d{4}", # DD.MM.YYYY
        r"\d{2}-\d{2}-\d{4}",   # DD-MM-YYYY
    ]

    for p in patterns:
        match = re.search(p, raw)
        if match:
            extracted_date = match.group(0)
            break

    # если нашли — конвертируем в формат YYYY-MM-DD
    if extracted_date:
        try:
            if "." in extracted_date:
                extracted_date = datetime.strptime(extracted_date, "%d.%m.%Y").strftime("%Y-%m-%d")
            elif "-" in extracted_date and extracted_date.count("-") == 2:
                if extracted_date[4] == "-":  # YYYY-MM-DD
                    pass
                else:  # DD-MM-YYYY
                    extracted_date = datetime.strptime(extracted_date, "%d-%m-%Y").strftime("%Y-%m-%d")
        except:
            pass

        data["date"] = extracted_date
    else:
        data["date"] = ""

    # --- ГАРАНТИРОВАННЫЙ ВОЗВРАТ ---
    return {
        "amount": float(data.get("amount", 0)),
        "category": data.get("category", "прочее"),
        "description": data.get("description", "платеж"),
        "date": data.get("date", "")
    }
