import re

def parse_transaction_text(text: str):
    # ищем первое число
    m = re.search(r"(\d[\d\s,.]*)", text)
    if not m:
        return None
    raw = m.group(1)
    clean = re.sub(r"[^\d.]", "", raw)
    try:
        amt = float(clean)
    except:
        return None
    # простая категория по слову
    cat = "прочее"
    if "такси" in text.lower():
        cat = "транспорт"
    if "еда" in text.lower() or "ресторан" in text.lower():
        cat = "еда"
    return {"amount": amt, "category": cat, "description": text}
