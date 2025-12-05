import re
from datetime import datetime

def extract_amount(text):
    # Находит сумму вида 5 000 000, 5000000.00 и т.п.
    match = re.search(r"(\d[\d\s]{3,}(?:\.\d{2})?)", text)
    if match:
        raw = match.group(1)
        num = raw.replace(" ", "")
        return float(num)
    return None


def extract_date(text):
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    if match:
        return match.group(1)
    return None


def extract_name(text):
    # УZCARD часто содержит имя плательщика
    match = re.search(r"[A-ZА-Я][A-ZА-Я]+ [A-ZА-Я]+ [A-ZА-Я]+", text.upper())
    return match.group(0).title() if match else None


def build_description(text, name):
    if name:
        return f"Платёж — {name}"
    return "Оплата по чеку"
