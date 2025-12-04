def fmt_currency(value):
    """
    Форматирует число в красивый денежный формат:
    15000 → 15 000.00
    """
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except:
        return str(value)


def fmt_percent(value):
    """
    Форматирует процент:
    0.156 → 15.6%
    """
    try:
        return f"{value * 100:.1f}%"
    except:
        return value
