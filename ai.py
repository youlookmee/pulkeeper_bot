# ai.py — GPT-4.1-mini Integration for PulKeeper v3.0
import os
import json
from openai import OpenAI

# New correct client initialization
client = OpenAI()   # автоматически возьмёт OPENAI_API_KEY из окружения

async def analyze_message(text: str):
    """
    Sends user message to GPT-4.1-mini and expects structured JSON output.
    """
    prompt = f"""
You are an AI finance assistant. Your task is to read the user's message
and convert it into a structured JSON transaction.

The user may write in Russian, Uzbek, or English.

Your output MUST be ONLY valid JSON with no explanations.

JSON format:
{{
  "type": "expense" | "income" | "unknown",
  "amount": number|null,
  "category": string|null,
  "title": string|null,
  "description": string|null,
  "date": "YYYY-MM-DD",
  "valid": true|false,
  "reason": string
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message["content"]

    try:
        data = json.loads(raw)
    except:
        return {"valid": False, "reason": "Invalid JSON from model"}

    return data
