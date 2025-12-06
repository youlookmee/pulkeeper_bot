from pydantic import BaseModel
from typing import Optional

class UserModel(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
