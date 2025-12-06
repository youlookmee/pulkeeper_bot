from pydantic import BaseModel

class StatsModel(BaseModel):
    expenses: float
    income: float
    balance: float
    transactions_count: int
