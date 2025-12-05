from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Numeric, Text, Date, TIMESTAMP, func
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

Base = declarative_base()

# -----------------------------
# Таблица транзакций
# -----------------------------
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


# -----------------------------
# Подключение к базе
# -----------------------------
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db():
    """Создаёт таблицы, если их нет."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Получаем новую сессию подключения."""
    return SessionLocal()


# ============================================================
# 📌 ФУНКЦИИ РАБОТЫ С ТРАНЗАКЦИЯМИ
# ============================================================

def save_transaction(user_id: int, amount: float, category: str, tx_type: str, description: str, date):
    """
    Создаёт новую транзакцию (универсально для текста и OCR чеков).
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
    session.close()

    return tx.id  # возвращаем ID для кнопок «Одобрить / Отклонить»


def update_transaction(tx_id: int, **fields):
    """
    Обновляет транзакцию по ID. Например:
    update_transaction(5, amount=20000, category="еда")
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


def delete_transaction(tx_id: int):
    """
    Удаляет транзакцию. Для кнопки «Отклонить».
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
