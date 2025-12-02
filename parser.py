import re
from typing import Optional, Tuple


CATEGORY_PATTERNS = {
    "food": ["obid", "obed", "ovqat", "choy", "kofe", "kafe", "coffee", "eat", "food", "pizza", "non", "pitsa"],
    "transport": ["taksi", "taxi", "avtobus", "bus", "metro", "benzin", "gaz", "yoqilgi"],
    "shopping": ["market", "magazin", "xarid", "shop", "supermarket", "olmoq"],
    "home": ["uy", "svet", "arenda", "rent", "kommunal", "kvartira", "dom"],
    "health": ["dori", "apteka", "doctor", "lekar", "med", "apteka"],
    "fun": ["kino", "film", "movie", "game", "oyin", "park"],
    "services": ["xizmat", "service", "remont", "moyka", "repair"],
}


CATEGORY_LABELS = {
    "food": {"uz": "🍽 Ovqat", "ru": "🍽 Еда"},
    "transport": {"uz": "🚕 Transport", "ru": "🚕 Транспорт"},
    "shopping": {"uz": "🛍 Xarid", "ru": "🛍 Покупки"},
    "home": {"uz": "🏠 Uy", "ru": "🏠 Дом"},
    "health": {"uz": "🏥 Sog'liq", "ru": "🏥 Здоровье"},
    "fun": {"uz": "🎬 Ko'ngilochar", "ru": "🎬 Развлечения"},
    "services": {"uz": "🛠 Xizmat", "ru": "🛠 Услуги"},
    "other": {"uz": "❓ Boshqa", "ru": "❓ Другое"},
}


def detect_category(text: str):
    lower = text.lower()
    for key, words in CATEGORY_PATTERNS.items():
        if any(w in lower for w in words):
            return key
    return "other"


def parse_expense(text: str) -> Optional[Tuple[str, int, str]]:
    match = re.search(r'(\d[\d\s]*)', text)
    if not match:
        return None

    amount_str = match.group(1).replace(" ", "")
    try:
        amount = int(amount_str)
    except ValueError:
        return None

    title = text.replace(match.group(1), "").strip() or "Xarajat"
    category_key = detect_category(title)

    return title, amount, category_key
