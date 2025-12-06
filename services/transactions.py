from .db import get_session, Transaction

def save_transaction(user_id: int, amount: float, category: str, tx_type: str, description: str, date=None):
    """
    Сохраняет транзакцию и возвращает id.
    Использовать так: save_transaction(user_id, amount, category, tx_type, description, date)
    """
    session = get_session()
    tx = Transaction(
        user_id=user_id,
        amount=amount,
        category=category,
        type=tx_type,
        description=description,
        tx_date=date
    )
    session.add(tx)
    session.commit()
    tx_id = tx.id
    session.close()
    return tx_id

def delete_transaction(tx_id: int):
    session = get_session()
    tx = session.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        session.close()
        return False
    session.delete(tx)
    session.commit()
    session.close()
    return True
