# services/db.py
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String,
    Numeric, Text, Date, TIMESTAMP, func
)
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

Base = declarative_base()


# ============================================================
# 📌 Таблица транзакций
# ============================================================
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    type = Column(String(10))              # income | expense
    amount = Column(Numeric(14, 2))
    category = Column(String(100))
    description = Column(Text)
    tx_date = Column(Date, server_default=func.current_date())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# ============================================================
# 📌 Подключение к базе
# ============================================================
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db():
    """Создаёт таблицы, если их нет."""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()


# ============================================================
# 📌 СОХРАНЕНИЕ ТРАНЗАКЦИЙ
# ============================================================
def save_transaction(user_id: int, amount: float, category: str, tx_type: str, description: str, date):
    """
    Создаёт новую транзакцию. Возвращает ID.
    """
    session = get_session()

    tx = Transaction(
        user_id=user_id,
        amount=amount,
        category=category,
        type=tx_type,
        description=description,
        tx_date=date,
    )

    session.add(tx)
    session.commit()
    tx_id = tx.id
    session.close()

    return tx_id


# ============================================================
# 📌 ОБНОВЛЕНИЕ ТРАНЗАКЦИИ
# ============================================================
def update_transaction(tx_id: int, **fields):
    """
    Обновляет поля транзакции по её ID.
    """
    session = get_session()
    tx = session.query(Transaction).filter(Transaction.id == tx_id).first()

    if not tx:
        session.close()
        return False

    for key, val in fields.items():
        setattr(tx, key, val)

    session.commit()
    session.close()
    return True


# ============================================================
# 📌 УДАЛЕНИЕ ТРАНЗАКЦИИ
# ============================================================
def delete_transaction(tx_id: int):
    """
    Удаляет транзакцию.
    """
    session = get_session()
    tx = session.query(Transaction).filter(Transaction.id == tx_id).first()

    if not tx:
        session.close()
        return False

    session.delete(tx)
    session.commit()
    session.close()
    return True


# ============================================================
# 📊 СТАТИСТИКА ДЛЯ ОТЧЁТОВ (КАК В THEOAI)
# ============================================================
def get_user_stats(user_id: int):
    """
    Возвращает словарь:
    {
        "income": float,
        "expense": float,
        "count": int,
        "balance": float
    }
    """
    session = get_session()

    income = session.query(func.sum(Transaction.amount)) \
        .filter(Transaction.user_id == user_id, Transaction.type == "income") \
        .scalar() or 0

    expense = session.query(func.sum(Transaction.amount)) \
        .filter(Transaction.user_id == user_id, Transaction.type == "expense") \
        .scalar() or 0

    count = session.query(func.count(Transaction.id)) \
        .filter(Transaction.user_id == user_id) \
        .scalar() or 0

    balance = income - expense

    session.close()

    return {
        "income": float(income),
        "expense": float(expense),
        "count": int(count),
        "balance": float(balance)
    }
