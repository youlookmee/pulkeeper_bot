import re
from typing import Optional, Tuple

CATEGORIES = {
    "food": (["obid", "obed", "ovqat", "choy", "kofe", "cofe", "food", "eat", "non", "fastfood"], "🍽 Eда/Ovqat"),
    "transport": (["taksi", "taxi", "avtobus", "bus", "metro", "benzin", "gaz"], "🚕 Transport"),
    "shopping": (["market", "shop", "xarid", "olmoq", "pokup", "magazin"], "🛍 Xarid"),
    "home": (["uy", "svet", "arenda", "kvartira", "gaz svet", "kommunal"], "🏠 Uy"),
    "health": (["dori", "apteka", "doctor", "lekar", "med"], "🏥 Sog'liq"),
    "fun": (["kino", "film", "park", "game", "pubg"], "🎬 Ko'ngilochar"),
    "services": (["xizmat", "service", "remont", "moyka"], "🛠 Xizmatlar")
}

def detect_category(text: str):
    lower = text.lower()
    for _, (words, label) in CATEGORIES.items():
        if any(w in lower for w in words):
            return label
    return "❓ Boshqa"

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
    category = detect_category(title)

    return title, amount, category
