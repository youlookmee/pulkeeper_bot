# models.py
from sqlalchemy import Column, Integer, BigInteger, String, Numeric, Text, Date, TIMESTAMP, func
from services.db import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    type = Column(String(10), nullable=False)        # 'expense' или 'income'
    amount = Column(Numeric(14, 2), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    tx_date = Column(Date, server_default=func.current_date())
