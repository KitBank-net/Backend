from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    interest_rate = Column(Float, default=5.0)
    term_months = Column(Integer, nullable=False)
    purpose = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, approved, paid
    remaining_balance = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
