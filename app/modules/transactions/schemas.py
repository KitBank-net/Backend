from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionBase(BaseModel):
    account_id: int
    amount: float
    currency: str
    transaction_type: str

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    status: Optional[str] = None

class TransactionResponse(TransactionBase):
    id: int
    status: str
    reference_code: str
    created_at: datetime

    class Config:
        from_attributes = True
