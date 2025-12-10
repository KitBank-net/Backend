from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# Enums
class AccountTypeEnum(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"


class CurrencyEnum(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class AccountStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    CLOSED = "closed"


class AccountTierEnum(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# Account Creation
class AccountCreateRequest(BaseModel):
    """Request to create a new account"""
    account_type: AccountTypeEnum = AccountTypeEnum.CHECKING
    currency: CurrencyEnum = CurrencyEnum.USD
    account_tier: Optional[AccountTierEnum] = AccountTierEnum.BASIC


class AccountResponse(BaseModel):
    """Complete account details"""
    id: int
    user_id: int
    account_number: str
    routing_number: Optional[str]
    swift_code: Optional[str]
    iban: Optional[str]
    account_type: str
    currency: str
    account_tier: str
    current_balance: Decimal
    available_balance: Decimal
    ledger_balance: Decimal
    overdraft_limit: Decimal
    overdraft_enabled: bool
    interest_rate: Decimal
    minimum_balance: Decimal
    daily_transaction_limit: Decimal
    daily_withdrawal_limit: Decimal
    monthly_transaction_limit: Decimal
    check_writing_enabled: bool
    wire_transfer_enabled: bool
    ach_transfer_enabled: bool
    international_transfer_enabled: bool
    direct_deposit_enabled: bool
    bill_pay_enabled: bool
    debit_card_enabled: bool
    account_status: str
    opened_date: date
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    """Account balance information"""
    account_id: int
    account_number: str
    current_balance: Decimal
    available_balance: Decimal
    ledger_balance: Decimal
    currency: str


class AllBalancesResponse(BaseModel):
    """All account balances for a user"""
    accounts: list[BalanceResponse]
    total_balance_usd: Decimal


class TransactionLimitsUpdate(BaseModel):
    """Update transaction limits"""
    daily_transaction_limit: Optional[Decimal] = Field(None, ge=0, le=100000)
    daily_withdrawal_limit: Optional[Decimal] = Field(None, ge=0, le=50000)
    monthly_transaction_limit: Optional[Decimal] = Field(None, ge=0, le=500000)


class AccountSettingsUpdate(BaseModel):
    """Update account settings"""
    overdraft_enabled: Optional[bool] = None
    check_writing_enabled: Optional[bool] = None
    wire_transfer_enabled: Optional[bool] = None
    ach_transfer_enabled: Optional[bool] = None
    international_transfer_enabled: Optional[bool] = None


class AccountClosureRequest(BaseModel):
    """Request account closure"""
    reason: str = Field(..., min_length=10, max_length=500)
    transfer_remaining_balance_to: Optional[int] = None  # Account ID


class StatementRequest(BaseModel):
    """Request account statement"""
    start_date: date
    end_date: date
    format: str = Field(default="pdf", pattern="^(pdf|csv)$")
