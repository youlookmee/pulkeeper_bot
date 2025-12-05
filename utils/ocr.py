from openai import OpenAI
import base64
import json
import os
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_from_image(image_bytes: bytes):
    """
    OCR через GPT-4o-mini Vision (НОВЫЙ API).
    """

    encoded = base64.b64encode(image_bytes).decode("utf-8")

    system_prompt = """
Ты ассистент, который извлекает данные с чеков.
Верни строго JSON:

{
  "amount": 0,
  "category": "",
  "description": "",
  "date": ""
}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Извлеки данные с чека"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded}"
                    }
                ]
            }
        ]
    )

    raw = response.output_text
    print("\n--- GPT RAW OCR ---\n", raw, "\n-------------------\n")

    try:
        json_text = re.search(r"\{[\s\S]*\}", raw).group(0)
        data = json.loads(json_text)
    except:
        return None

    return data
