from openai import OpenAI
import base64
import re
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_from_image(image_bytes: bytes):
    """
    Распознаёт чек через GPT-4o mini Vision.
    Возвращает dict: amount, category, description, date
    """

    # Кодируем картинку в base64
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
Ты — OCR ассистент для финансовых чеков. 
Твоя задача: понять сумму, описание и категорию.
Верни строго JSON:

{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}

Правила:
- Сумму ищи как самое большое число в формате 5 000 000 или 7000000 или 7 000 000.00
- Категория: проанализируй текст и выбери тип:
  "еда", "развлечения", "покупки", "транспорт", "прочее", "другое".
- description — кратко объясни назначение платежа.
- Если дата не найдена, оставь пустую строку.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Найди данные на чеке"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded}"
                    }
                ]
            }
        ]
    )

    try:
        raw = response.choices[0].message.content
        print("GPT OCR RAW:", raw)

        # Ищем JSON в ответе
        json_text = re.search(r"\{(.|\n)*\}", raw).group(0)

        import json
        data = json.loads(json_text)

        return data

    except Exception as e:
        print("OCR JSON ERROR:", e)
        return None
