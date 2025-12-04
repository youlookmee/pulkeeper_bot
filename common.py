def parse_number(text: str):
    """
    Превращает строку в число.
    Поддерживает формат 1500, 1.500, 1,500, 1 500.
    """
    try:
        cleaned = text.replace(" ", "").replace(",", ".")
        return float(cleaned)
    except:
        return None
