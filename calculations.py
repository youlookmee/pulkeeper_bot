import math

def compute_financials(data):
    """
    На вход получает словарь с данными:
    {
        "income": 0,
        "expenses": 0,
        "savings": 0,
        "loans": 0,
        "assets": 0
    }

    Возвращает словарь с финальными расчетами.
    """

    income = float(data.get("income", 0))
    expenses = float(data.get("expenses", 0))
    savings = float(data.get("savings", 0))
    loans = float(data.get("loans", 0))
    assets = float(data.get("assets", 0))

    # 📊 1. Net Worth
    net_worth = assets - loans

    # 📉 2. Monthly surplus
    monthly_surplus = income - expenses

    # 💰 3. Saving rate
    saving_rate = (savings / income) if income > 0 else 0

    # 🧱 4. Debt ratio
    if assets > 0:
        debt_ratio = loans / assets
    else:
        debt_ratio = 1 if loans > 0 else 0

    # 🛟 5. Reserve months
    if expenses > 0:
        months_of_reserve = round(savings / expenses, 1)
    else:
        months_of_reserve = "∞"

    # ⭐ 6. Financial score (0–100)
    # Простая формула, которую можно улучшить позже
    score = 50

    # влияние ежемесячного остатка
    score += max(min((monthly_surplus / max(expenses, 1)) * 40, 20), -20)

    # влияние saving_rate
    score += max(min(saving_rate * 40, 15), -15)

    # влияние долгов
    score += max(min((1 - debt_ratio) * 25, 25), -25)

    score = max(0, min(100, round(score)))

    return {
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "loans": loans,
        "assets": assets,
        "net_worth": net_worth,
        "monthly_surplus": monthly_surplus,
        "saving_rate": saving_rate,
        "debt_ratio": debt_ratio,
        "months_of_reserve": months_of_reserve,
        "score": score
    }
