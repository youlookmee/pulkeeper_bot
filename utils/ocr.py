import base64
import re
import json
import os
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def _extract_json_from_text(raw_text: str):
    m = re.search(r"\{[\s\S]*\}", raw_text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except:
        return None

def extract_from_image(image_bytes: bytes):
    """
    Возвращает dict: {amount, category, description, date} или None.
    """
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
Ты — OCR ассистент для чеков (коротко). Верни ТОЛЬКО чистый JSON:
{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}
Сумму вернуть как число, без пробелов/разделителей.
Если не уверен — оставь пустую строку или 0.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "input_text", "text": "Найди сумму, категорию, описание, дату"},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}"}
                ]}
            ]
        )
        raw = response.choices[0].message.content
        # попытаемся получить JSON
        data = _extract_json_from_text(raw)
        if not data:
            return None
        # чистим сумму
        try:
            amt = data.get("amount", 0)
            # если строка с пробелами/запятыми
            if isinstance(amt, str):
                clean = re.sub(r"[^\d.]", "", amt)
                amt = float(clean) if clean else 0.0
            else:
                amt = float(amt)
            data["amount"] = amt
        except:
            data["amount"] = 0.0
        return {
            "amount": data.get("amount", 0.0),
            "category": data.get("category", "прочее"),
            "description": data.get("description", ""),
            "date": data.get("date", "")
        }
    except Exception as e:
        print("OCR ERROR:", e)
        return None
