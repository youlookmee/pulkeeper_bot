from pydantic import BaseModel
from typing import Optional

class OCRResult(BaseModel):
    amount: float
    category: str
    description: str
    date: Optional[str] = ""
