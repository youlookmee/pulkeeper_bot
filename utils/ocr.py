import base64
import requests
from config import DEEPSEEK_API_KEY


def ocr_ai(image_bytes: bytes) -> str:
    url = "https://api.deepseek.com/v1/chat/completions"

    img_b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Extract all text from this receipt photo. Return ONLY raw text."},
            {"role": "user", "content": [{"type": "input_image", "image_base64": img_b64}]}
        ]
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers).json()
        return r["choices"][0]["message"]["content"]
    except:
        return ""


def read_text(image_bytes: bytes) -> str:
    return ocr_ai(image_bytes)
