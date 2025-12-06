# services/save_transaction.py
from services.db import get_session, Transaction
from decimal import Decimal
from typing import Dict, Any

def save_transaction(user_id: int, data: Dict[str, Any]) -> int:
    """
    Сохраняет транзакцию в БД.
    data expected keys: amount, category, description, date (date optional)
    Возвращает id добавленной транзакции.
    """
    # безопасные значения
    amount = data.get("amount", 0) or 0
    try:
        amount = Decimal(str(amount))
    except Exception:
        amount = Decimal("0")

    category = data.get("category", "прочее")
    description = data.get("description", "")
    tx_date = data.get("date", None)  # если пусто — SQLAlchemy подставит current_date

    session = get_session()
    tx = Transaction(
        user_id=user_id,
        type="expense" if amount >= 0 else "income",  # если нужно — поменяй логику
        amount=amount,
        category=category,
        description=description,
        tx_date=tx_date or None
    )

    session.add(tx)
    session.commit()
    tx_id = tx.id
    session.close()
    return tx_id
