import base64
import requests
from config import DEEPSEEK_API_KEY


def extract_from_receipt(image_bytes: bytes) -> str:
    url = "https://api.deepseek.com/v1/chat/completions"

    prompt = """
    Ты — эксперт по парсингу чеков.  
    Распознай текст на изображении чека и верни JSON строго в формате:

    {
      "total": число,
      "items": [
         {"name": "...", "price": число},
      ],
      "raw_text": "...",
      "date": "2025-01-01"
    }

    Если данных нет — ставь null.
    """

    img_base64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_base64": img_base64}
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers).json()

    import json
    try:
        return json.loads(response["choices"][0]["message"]["content"])
    except:
        return None
