# db.py
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Numeric, Text, Date, TIMESTAMP, func
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

Base = declarative_base()

# Таблица транзакций
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    type = Column(String(10))          # income | expense
    amount = Column(Numeric(14, 2))
    category = Column(String(100))
    description = Column(Text)
    tx_date = Column(Date, server_default=func.current_date())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# Создаем подключение к базе
engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db():
    """Создаёт таблицы, если их нет."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Получаем новую сессию подключения."""
    return SessionLocal()
