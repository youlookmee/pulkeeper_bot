import re

def parse_expense(text: str):
    match = re.search(r'(\d[\d\s]*)', text)
    if not match:
        return None
    amount = int(match.group(1).replace(" ", ""))
    title = text.replace(match.group(1), "").strip() or "Xarajat"
    return title, amount
