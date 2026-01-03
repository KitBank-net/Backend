from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum


# ============================================================
# Enums (matching models.py)
# ============================================================

class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    P2P = "p2p"
    QR_PAYMENT = "qr_payment"
    BILL_PAYMENT = "bill_payment"
    MOBILE_MONEY = "mobile_money"
    INTERNATIONAL = "international"
    CARD_PAYMENT = "card_payment"
    MERCHANT_PAYMENT = "merchant_payment"
    LOAN_DISBURSEMENT = "loan_disbursement"
    LOAN_REPAYMENT = "loan_repayment"
    FEE = "fee"
    REFUND = "refund"
    REVERSAL = "reversal"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"
    ON_HOLD = "on_hold"


class TransactionChannel(str, Enum):
    WEB = "web"
    MOBILE_APP = "mobile_app"
    API = "api"
    USSD = "ussd"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    ATM = "atm"
    POS = "pos"
    BRANCH = "branch"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    KES = "KES"
    NGN = "NGN"
    ZAR = "ZAR"
    RWF = "RWF"
    UGX = "UGX"
    TZS = "TZS"


# ============================================================
# Base Schemas
# ============================================================

class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    currency: Currency = Currency.USD
    description: Optional[str] = Field(None, max_length=500)
    narration: Optional[str] = Field(None, max_length=200)


# ============================================================
# Internal Transfer (Between own accounts)
# ============================================================

class InternalTransferRequest(TransactionBase):
    source_account_id: int
    destination_account_id: int
    
    @validator('destination_account_id')
    def accounts_must_be_different(cls, v, values):
        if 'source_account_id' in values and v == values['source_account_id']:
            raise ValueError('Source and destination accounts must be different')
        return v


# ============================================================
# P2P Transfer (To another user)
# ============================================================

class P2PTransferRequest(TransactionBase):
    source_account_id: int
    # Can specify recipient by account number, phone, or email
    recipient_account_number: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    
    @validator('recipient_email', always=True)
    def at_least_one_recipient(cls, v, values):
        if not v and not values.get('recipient_account_number') and not values.get('recipient_phone'):
            raise ValueError('Must provide recipient_account_number, recipient_phone, or recipient_email')
        return v


# ============================================================
# QR Payment
# ============================================================

class QRCodeGenerateRequest(BaseModel):
    account_id: int
    amount: Optional[Decimal] = Field(None, gt=0, description="Fixed amount (optional)")
    currency: Currency = Currency.USD
    expires_in_hours: Optional[int] = Field(24, ge=1, le=720)


class QRCodeResponse(BaseModel):
    id: int
    account_id: int
    qr_code_data: str
    qr_code_image_url: Optional[str]
    amount: Optional[Decimal]
    currency: Currency
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class QRPaymentRequest(TransactionBase):
    source_account_id: int
    qr_code_data: str


# ============================================================
# Bill Payment
# ============================================================

class BillPaymentRequest(TransactionBase):
    source_account_id: int
    biller_code: str = Field(..., description="Unique code for the biller")
    bill_reference: str = Field(..., description="Account/reference number with the biller")
    

class BillerInfo(BaseModel):
    biller_code: str
    biller_name: str
    category: str  # utilities, telecom, government, etc.
    min_amount: Optional[Decimal]
    max_amount: Optional[Decimal]


# ============================================================
# Mobile Money
# ============================================================

class MobileMoneyProvider(str, Enum):
    MPESA = "mpesa"
    MTN_MOMO = "mtn_momo"
    AIRTEL_MONEY = "airtel_money"
    ORANGE_MONEY = "orange_money"
    TIGO_PESA = "tigo_pesa"


class MobileMoneyTransferRequest(TransactionBase):
    source_account_id: int
    provider: MobileMoneyProvider
    mobile_number: str = Field(..., pattern=r'^\+?[1-9]\d{6,14}$')
    recipient_name: Optional[str] = None


class MobileMoneyDepositRequest(TransactionBase):
    destination_account_id: int
    provider: MobileMoneyProvider
    mobile_number: str = Field(..., pattern=r'^\+?[1-9]\d{6,14}$')


# ============================================================
# International Transfer
# ============================================================

class InternationalTransferRequest(TransactionBase):
    source_account_id: int
    
    # Beneficiary Details
    beneficiary_name: str = Field(..., min_length=2, max_length=200)
    beneficiary_address: Optional[str] = None
    beneficiary_country: str = Field(..., min_length=2, max_length=100)
    
    # Bank Details
    bank_name: str
    swift_code: str = Field(..., pattern=r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')
    iban: Optional[str] = Field(None, max_length=34)
    routing_number: Optional[str] = None
    account_number: str
    
    # Purpose
    purpose_code: str = Field(..., description="Purpose of transfer code")
    purpose_description: Optional[str] = None
    
    # FX
    destination_currency: Optional[Currency] = None


# ============================================================
# Transaction Response Schemas
# ============================================================

class TransactionResponse(BaseModel):
    id: int
    reference_code: str
    
    # Accounts
    source_account_id: Optional[int]
    source_account_number: Optional[str]
    destination_account_id: Optional[int]
    destination_account_number: Optional[str]
    
    # Beneficiary
    beneficiary_name: Optional[str]
    
    # Amounts
    amount: Decimal
    currency: Currency
    fee_amount: Decimal
    total_amount: Decimal
    
    # FX
    original_amount: Optional[Decimal]
    original_currency: Optional[Currency]
    exchange_rate: Optional[Decimal]
    
    # Type and Status
    transaction_type: TransactionType
    status: TransactionStatus
    channel: TransactionChannel
    
    # Description
    description: Optional[str]
    narration: Optional[str]
    
    # Timestamps
    initiated_at: datetime
    completed_at: Optional[datetime]
    
    # Failure info
    failure_reason: Optional[str]
    
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# Transaction History Filters
# ============================================================

class TransactionHistoryFilter(BaseModel):
    account_id: Optional[int] = None
    transaction_type: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None
    currency: Optional[Currency] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_code: Optional[str] = None


# ============================================================
# Fee Calculation
# ============================================================

class FeeCalculationRequest(BaseModel):
    transaction_type: TransactionType
    amount: Decimal
    currency: Currency


class FeeCalculationResponse(BaseModel):
    transaction_type: TransactionType
    amount: Decimal
    currency: Currency
    fee_amount: Decimal
    total_amount: Decimal
    fee_breakdown: dict  # flat_fee, percentage_fee, etc.


# ============================================================
# FX Rate
# ============================================================

class ExchangeRateRequest(BaseModel):
    from_currency: Currency
    to_currency: Currency
    amount: Decimal


class ExchangeRateResponse(BaseModel):
    from_currency: Currency
    to_currency: Currency
    rate: Decimal
    amount: Decimal
    converted_amount: Decimal
    valid_until: datetime


# ============================================================
# Transaction Approval (for high-value transactions)
# ============================================================

class TransactionApprovalRequest(BaseModel):
    transaction_id: int
    approved: bool
    notes: Optional[str] = None


# ============================================================
# Transaction Reversal
# ============================================================

class TransactionReversalRequest(BaseModel):
    transaction_id: int
    reason: str = Field(..., min_length=10, max_length=500)
