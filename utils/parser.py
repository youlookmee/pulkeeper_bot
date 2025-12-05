# finbot/utils/parser.py
import re
from datetime import datetime

# Категории примеров (можно расширить позже)
CATEGORY_KEYWORDS = {
    "еда": ["еда", "обед", "завтрак", "ужин", "кафе", "рест", "бургер"],
    "транспорт": ["такси", "авто", "машина", "бензин", "транспорт"],
    "продукты": ["магазин", "продукты", "супермаркет"],
    "здоровье": ["аптека", "лекарства", "здоровье"],
    "одежда": ["одежда", "шмот", "ботинки", "футболка"],
    "зарплата": ["зарплата", "аванс", "доход"],
    "подарок": ["подарок", "дар"],
}


def extract_amount(text: str):
    """
    Извлекает сумму: 12000, 12.000, 12 000, 1.2 млн, 30k и т.д.
    """
    text = text.lower()

    # 1) Формат "30к", "50k"
    k_match = re.search(r"(\d+)[kк]", text)
    if k_match:
        return float(k_match.group(1)) * 1000

    # 2) Формат "1.2 млн"
    mln = re.search(r"(\d+[\.,]?\d*)\s*млн", text)
    if mln:
        return float(mln.group(1).replace(",", ".")) * 1_000_000

    # 3) Обычные суммы
    numbers = re.findall(r"\d[\d\s\.,]*", text)
    if numbers:
        num = numbers[0].replace(" ", "").replace(",", "").replace(".", "")
        return float(num)

    return None


def detect_type(text: str):
    text = text.lower()
    income_words = ["зарплата", "доход", "получил", "поступление"]
    if any(word in text for word in income_words):
        return "income"
    return "expense"


def detect_category(text: str):
    text = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return category
    return "прочее"


def parse_transaction(text: str):
    """
    Возвращает dict:
    {
      "amount": 50000,
      "type": "expense",
      "category": "еда",
      "description": "ужин",
      "date": today
    }
    """

    amount = extract_amount(text)
    if not amount:
        return None

    tx_type = detect_type(text)
    category = detect_category(text)

    return {
        "amount": amount,
        "type": tx_type,
        "category": category,
        "description": text,
        "date": datetime.now().date()
    }
