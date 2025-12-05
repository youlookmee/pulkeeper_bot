import json
import re

with open("models/categories.json", "r", encoding="utf-8") as f:
    CATS = json.load(f)

def categorize(text):
    for category, words in CATS.items():
        for w in words:
            if re.search(w, text, re.IGNORECASE):
                return category
    return "прочее"
