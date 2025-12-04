import requests
from config import WHISPER_API_KEY

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

def transcribe_voice(file_path: str) -> str:
    """
    Получает путь к аудиофайлу и возвращает распознанный текст через OpenAI Whisper.
    """

    headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}"
    }

    with open(file_path, "rb") as audio_file:
        files = {
            "file": audio_file,
            "model": (None, "whisper-1")
        }

        try:
            response = requests.post(WHISPER_URL, headers=headers, files=files)
            data = response.json()
            return data.get("text", "Ошибка: Whisper не вернул текст.")

        except Exception as e:
            return f"Ошибка при распознавании аудио: {e}"
