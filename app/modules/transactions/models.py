from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TransactionType(str, enum.Enum):
    """Types of transactions"""
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


class TransactionStatus(str, enum.Enum):
    """Transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"
    ON_HOLD = "on_hold"


class TransactionChannel(str, enum.Enum):
    """Channel through which transaction was initiated"""
    WEB = "web"
    MOBILE_APP = "mobile_app"
    API = "api"
    USSD = "ussd"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    ATM = "atm"
    POS = "pos"
    BRANCH = "branch"


class Currency(str, enum.Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    KES = "KES"  # Kenyan Shilling
    NGN = "NGN"  # Nigerian Naira
    ZAR = "ZAR"  # South African Rand
    RWF = "RWF"  # Rwandan Franc
    UGX = "UGX"  # Ugandan Shilling
    TZS = "TZS"  # Tanzanian Shilling


class Transaction(Base):
    """Enhanced transaction model with full banking features"""
    __tablename__ = "transactions"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Reference
    reference_code = Column(String(50), unique=True, nullable=False, index=True)
    external_reference = Column(String(100), nullable=True)  # Third-party reference
    
    # Source Account
    source_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    source_account_number = Column(String(20), nullable=True)
    
    # Destination Account
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    destination_account_number = Column(String(20), nullable=True)
    destination_bank_code = Column(String(20), nullable=True)  # For external transfers
    destination_bank_name = Column(String(100), nullable=True)
    
    # Beneficiary Details (for external transfers)
    beneficiary_name = Column(String(200), nullable=True)
    beneficiary_phone = Column(String(20), nullable=True)
    beneficiary_email = Column(String(255), nullable=True)
    
    # Amount Details
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(SQLEnum(Currency), default=Currency.USD, nullable=False)
    
    # FX Details (for currency conversion)
    original_amount = Column(Numeric(15, 2), nullable=True)
    original_currency = Column(SQLEnum(Currency), nullable=True)
    exchange_rate = Column(Numeric(15, 6), nullable=True)
    
    # Fees
    fee_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    fee_currency = Column(SQLEnum(Currency), nullable=True)
    total_amount = Column(Numeric(15, 2), nullable=False)  # amount + fee
    
    # Transaction Details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    channel = Column(SQLEnum(TransactionChannel), default=TransactionChannel.API, nullable=False)
    
    # Description and Notes
    description = Column(String(500), nullable=True)
    narration = Column(String(200), nullable=True)  # Short description for statements
    internal_notes = Column(Text, nullable=True)  # Admin notes
    
    # QR Payment specific
    qr_code = Column(String(500), nullable=True)
    merchant_id = Column(String(50), nullable=True)
    merchant_name = Column(String(200), nullable=True)
    
    # Bill Payment specific
    biller_code = Column(String(50), nullable=True)
    biller_name = Column(String(200), nullable=True)
    bill_reference = Column(String(100), nullable=True)
    
    # Mobile Money specific
    mobile_money_provider = Column(String(50), nullable=True)  # M-Pesa, MTN, etc.
    mobile_number = Column(String(20), nullable=True)
    
    # International Transfer specific
    swift_code = Column(String(11), nullable=True)
    iban = Column(String(34), nullable=True)
    routing_number = Column(String(9), nullable=True)
    purpose_code = Column(String(10), nullable=True)
    
    # Processing Details
    initiated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Balance Tracking
    source_balance_before = Column(Numeric(15, 2), nullable=True)
    source_balance_after = Column(Numeric(15, 2), nullable=True)
    destination_balance_before = Column(Numeric(15, 2), nullable=True)
    destination_balance_after = Column(Numeric(15, 2), nullable=True)
    
    # Security & Audit
    ip_address = Column(String(45), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
    location = Column(String(200), nullable=True)
    
    # Flags
    is_recurring = Column(Boolean, default=False, nullable=False)
    is_scheduled = Column(Boolean, default=False, nullable=False)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Linked Transactions (for reversals, refunds)
    parent_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    source_account = relationship("Account", foreign_keys=[source_account_id])
    destination_account = relationship("Account", foreign_keys=[destination_account_id])
    parent_transaction = relationship("Transaction", remote_side=[id])
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, ref={self.reference_code}, type={self.transaction_type}, amount={self.amount})>"


class TransactionFee(Base):
    """Fee configuration for different transaction types"""
    __tablename__ = "transaction_fees"
    
    id = Column(Integer, primary_key=True, index=True)
    
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    currency = Column(SQLEnum(Currency), nullable=False)
    
    # Fee structure
    flat_fee = Column(Numeric(15, 2), default=0.00, nullable=False)
    percentage_fee = Column(Numeric(5, 4), default=0.0000, nullable=False)  # e.g., 0.0150 = 1.5%
    min_fee = Column(Numeric(15, 2), default=0.00, nullable=False)
    max_fee = Column(Numeric(15, 2), nullable=True)
    
    # Limits
    min_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    max_amount = Column(Numeric(15, 2), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class QRCode(Base):
    """QR codes for receiving payments"""
    __tablename__ = "qr_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    qr_code_data = Column(Text, nullable=False)
    qr_code_image_url = Column(String(500), nullable=True)
    
    # Optional: fixed amount QR
    amount = Column(Numeric(15, 2), nullable=True)
    currency = Column(SQLEnum(Currency), default=Currency.USD)
    
    # Validity
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    scan_count = Column(Integer, default=0, nullable=False)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", foreign_keys=[account_id])
