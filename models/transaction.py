from pydantic import BaseModel
from typing import Optional
from datetime import date

class TransactionModel(BaseModel):
    id: Optional[int] = None
    user_id: int
    amount: float
    category: str
    type: str           # income | expense
    description: Optional[str] = ""
    tx_date: Optional[date] = None
