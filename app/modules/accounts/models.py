from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date, Boolean, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class AccountType(str, enum.Enum):
    """Account type enumeration"""
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"


class Currency(str, enum.Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class AccountStatusEnum(str, enum.Enum):
    """Account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    CLOSED = "closed"


class AccountTier(str, enum.Enum):
    """Account tier"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class Account(Base):
    """Account model with complete banking features"""
    __tablename__ = "accounts"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Account Identifiers
    account_number = Column(String(12), unique=True, nullable=False, index=True)
    routing_number = Column(String(9), nullable=True)  # For US accounts
    swift_code = Column(String(11), nullable=True)  # For international transfers
    iban = Column(String(34), nullable=True)  # For European accounts
    
    # Account Configuration
    account_type = Column(SQLEnum(AccountType), default=AccountType.CHECKING, nullable=False)
    currency = Column(SQLEnum(Currency), default=Currency.USD, nullable=False)
    account_tier = Column(SQLEnum(AccountTier), default=AccountTier.BASIC, nullable=False)
    
    # Balances (using Numeric for precision with money)
    current_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    available_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    ledger_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    
    # Overdraft
    overdraft_limit = Column(Numeric(15, 2), default=0.00, nullable=False)
    overdraft_enabled = Column(Boolean, default=False, nullable=False)
    
    # Interest
    interest_rate = Column(Numeric(5, 4), default=0.0000, nullable=False)  # Annual percentage
    minimum_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    
    # Transaction Limits
    daily_transaction_limit = Column(Numeric(15, 2), default=10000.00, nullable=False)
    daily_withdrawal_limit = Column(Numeric(15, 2), default=5000.00, nullable=False)
    monthly_transaction_limit = Column(Numeric(15, 2), default=50000.00, nullable=False)
    
    # Account Features
    check_writing_enabled = Column(Boolean, default=False, nullable=False)
    wire_transfer_enabled = Column(Boolean, default=True, nullable=False)
    ach_transfer_enabled = Column(Boolean, default=True, nullable=False)
    international_transfer_enabled = Column(Boolean, default=True, nullable=False)
    direct_deposit_enabled = Column(Boolean, default=True, nullable=False)
    bill_pay_enabled = Column(Boolean, default=True, nullable=False)
    debit_card_enabled = Column(Boolean, default=True, nullable=False)
    
    # Status
    account_status = Column(SQLEnum(AccountStatusEnum), default=AccountStatusEnum.ACTIVE, nullable=False)
    opened_date = Column(Date, default=func.current_date(), nullable=False)
    closed_date = Column(Date, nullable=True)
    closure_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    
    def __repr__(self):
        return f"<Account(id={self.id}, account_number={self.account_number}, type={self.account_type})>"

