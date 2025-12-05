import re

def normalize_text(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", " ").lower()
    text = re.sub(r"\s+", " ", text)
    return text
