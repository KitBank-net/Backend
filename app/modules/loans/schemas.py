from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LoanBase(BaseModel):
    amount: float
    term_months: int
    purpose: str

class LoanCreate(LoanBase):
    user_id: int

class LoanUpdate(BaseModel):
    status: Optional[str] = None
    remaining_balance: Optional[float] = None

class LoanRepayment(BaseModel):
    amount: float

class LoanResponse(LoanBase):
    id: int
    user_id: int
    interest_rate: float
    status: str
    remaining_balance: float
    created_at: datetime

    class Config:
        from_attributes = True
