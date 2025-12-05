import base64
import requests
import pytesseract
from PIL import Image
from io import BytesIO
from config import DEEPSEEK_API_KEY


def ocr_ai(image_bytes: bytes) -> str:
    """OCR через DeepSeek Vision"""
    url = "https://api.deepseek.com/v1/chat/completions"

    img_b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Extract ALL visible text from this receipt photo."},
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
    

def ocr_tesseract(image_bytes: bytes) -> str:
    """OCR через Tesseract — идеально для UZCARD"""
    try:
        img = Image.open(BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang="rus+eng")
    except:
        return ""


def read_text(image_bytes: bytes) -> str:
    """Каскадное OCR — как у TheoAI"""
    text_ai = ocr_ai(image_bytes)
    text_tess = ocr_tesseract(image_bytes)

    if len(text_ai) > len(text_tess):
        return text_ai
    return text_tess
