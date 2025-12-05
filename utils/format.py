def money_format(amount: float) -> str:
    """
    Форматирование суммы:
    15000 → 15 тыс.
    150000 → 150 тыс.
    1500000 → 1.5 млн
    20000000 → 20 млн
    """
    try:
        amount = float(amount)
    except:
        return str(amount)

    # млн
    if amount >= 1_000_000:
        formatted = amount / 1_000_000
        if formatted.is_integer():
            return f"{int(formatted)} млн"
        else:
            return f"{formatted:.1f} млн"

    # тыс.
    if amount >= 10_000:
        formatted = amount / 1000
        if formatted.is_integer():
            return f"{int(formatted)} тыс."
        else:
            return f"{formatted:.1f} тыс."

    # меньше 10k — выводим как есть
    return f"{amount:,.0f}".replace(",", " ")
