import requests

OCR_API_KEY = "helloworld"  # бесплатный ключ OCR.Space


def ocr_read(image_bytes: bytes) -> str:
    """
    Отправляет фото в OCR.Space и возвращает распознанный текст.
    """

    url = "https://api.ocr.space/parse/image"

    files = {
        "file": ("image.jpg", image_bytes)
    }
    data = {
        "apikey": OCR_API_KEY,
        "language": "rus",
        "isTable": True
    }

    res = requests.post(url, files=files, data=data)
    result = res.json()

    try:
        return result["ParsedResults"][0]["ParsedText"]
    except:
        return ""
