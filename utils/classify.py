import re

CATEGORY_KEYWORDS = {
    "еда": ["кафе", "ресторан", "еда", "food", "бургер", "kfc", "мак", "шаверма", "doner"],
    "продукты": ["магазин", "market", "продукты", "supermarket", "гросс", "гурум", "корзинка"],
    "транспорт": ["такси", "yandex", "uber", "bus", "transport"],
    "развлечения": ["кино", "cinema", "movie", "театр"],
    "здоровье": ["аптека", "pharmacy"],
    "одежда": ["h&m", "zara", "befree", "clothes"],
}

def classify_category(text: str) -> str:
    text = text.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in text for w in words):
            return cat
    return "другое"


def classify_type(text: str) -> str:
    text = text.lower()
    if "зарплат" in text or "income" in text or "пополнен" in text:
        return "income"
    return "expense"
