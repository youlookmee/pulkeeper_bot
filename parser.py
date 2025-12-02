import re
from typing import Optional, Tuple

CATEGORY_PATTERNS = {
    "food": {
        "en": ["food", "eat", "meal", "lunch", "dinner", "coffee"],
        "ru": ["еда", "обед", "ужин", "завтрак", "кофе"],
        "uz": ["ovqat", "obid", "taom", "choy", "kofe"],
    },
    "transport": {
        "en": ["taxi", "bus", "metro"],
        "ru": ["такси", "автобус", "метро", "бензин"],
        "uz": ["taksi", "avtobus", "metro", "benzin"],
    },
    "shopping": {
        "en": ["market", "shop"],
        "ru": ["покупка", "магазин"],
        "uz": ["xarid", "bozor", "market"],
    },
}

CATEGORY_LABELS = {
    "food": {"uz": "🍽 Ovqat", "ru": "🍽 Еда", "en": "🍽 Food"},
    "transport": {"uz": "🚕 Transport", "ru": "🚕 Транспорт", "en": "🚕 Transport"},
    "shopping": {"uz": "🛍 Xarid", "ru": "🛍 Покупки", "en": "🛍 Shopping"},
    "other": {"uz": "❓ Boshqa", "ru": "❓ Другое", "en": "❓ Other"},
}


def detect_language(text: str) -> str:
    if re.search(r'[а-яА-Я]', text):
        return "ru"
    if re.search(r'[a-zA-Z]', text):
        return "en"
    return "uz"


def detect_category(text: str, lang: str) -> str:
    lower = text.lower()
    for key, langs in CATEGORY_PATTERNS.items():
        if lang in langs and any(w in lower for w in langs[lang]):
            return key
    return "other"


def parse_expense(text: str) -> Optional[Tuple[str, int, str, str]]:
    lang = detect_language(text)

    match = re.search(r'(\d[\d\s]*)', text)
    if not match:
        return None

    amount_str = match.group(1).replace(" ", "")
    try:
        amount = int(amount_str)
    except:
        return None

    title = text.replace(match.group(1), "").strip() or "expense"
    category_key = detect_category(title, lang)

    return title, amount, category_key, lang
