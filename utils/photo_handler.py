import base64
import requests
import json
from config import DEEPSEEK_API_KEY


def extract_from_receipt(image_bytes: bytes):
    """
    Отправляет фото чека в DeepSeek Vision и получает распознанный текст.
    """

    url = "https://api.deepseek.com/v1/images/vision"

    img_base64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "image_base64": img_base64,
        "task": "ocr",  # DeepSeek сам выберет лучший метод
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    # DeepSeek возвращает plain text, мы его и отдаём
    return data.get("text", "")
