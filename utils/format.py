def money_format(amount: float) -> str:
    """
    Форматирование суммы:
    150000 → 150,000
    20000 → 20,000
    """
    try:
        amount = float(amount)
    except:
        return str(amount)

    return f"{amount:,.0f}".replace(",", " ")
