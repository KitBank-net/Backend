from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text, Boolean, Enum as SQLEnum, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class LoanType(str, enum.Enum):
    """Types of loans offered"""
    PERSONAL = "personal"
    AUTO = "auto"
    HOME = "home"
    EDUCATION = "education"
    BUSINESS = "business"
    EMERGENCY = "emergency"
    SALARY_ADVANCE = "salary_advance"
    OVERDRAFT = "overdraft"


class LoanStatus(str, enum.Enum):
    """Loan application and lifecycle status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_DOCUMENTS = "pending_documents"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    OVERDUE = "overdue"
    DEFAULTED = "defaulted"
    PAID_OFF = "paid_off"
    CANCELLED = "cancelled"
    WRITTEN_OFF = "written_off"


class RepaymentFrequency(str, enum.Enum):
    """How often repayments are made"""
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class PaymentStatus(str, enum.Enum):
    """Status of individual payments"""
    SCHEDULED = "scheduled"
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    WAIVED = "waived"


class CollateralType(str, enum.Enum):
    """Types of collateral"""
    PROPERTY = "property"
    VEHICLE = "vehicle"
    SAVINGS = "savings"
    STOCKS = "stocks"
    GUARANTOR = "guarantor"
    SALARY = "salary"
    NONE = "none"


class LoanProduct(Base):
    """Loan products/types offered by the bank"""
    __tablename__ = "loan_products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    loan_type = Column(SQLEnum(LoanType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Interest rates
    min_interest_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 12.00%
    max_interest_rate = Column(Numeric(5, 2), nullable=False)
    default_interest_rate = Column(Numeric(5, 2), nullable=False)
    
    # Amount limits
    min_amount = Column(Numeric(15, 2), nullable=False)
    max_amount = Column(Numeric(15, 2), nullable=False)
    
    # Term limits (in months)
    min_term_months = Column(Integer, nullable=False)
    max_term_months = Column(Integer, nullable=False)
    
    # Fees
    processing_fee_percentage = Column(Numeric(5, 4), default=0.0)  # e.g., 0.02 = 2%
    processing_fee_flat = Column(Numeric(15, 2), default=0.0)
    late_payment_fee = Column(Numeric(15, 2), default=0.0)
    early_repayment_fee_percentage = Column(Numeric(5, 4), default=0.0)
    
    # Requirements
    requires_collateral = Column(Boolean, default=False)
    collateral_types = Column(String(200), nullable=True)  # CSV of allowed types
    min_credit_score = Column(Integer, nullable=True)
    min_income = Column(Numeric(15, 2), nullable=True)
    
    # Settings
    repayment_frequency = Column(SQLEnum(RepaymentFrequency), default=RepaymentFrequency.MONTHLY)
    grace_period_days = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Loan(Base):
    """Loan applications and active loans"""
    __tablename__ = "loans"
    
    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)  # Disbursement account
    product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False)
    
    # Loan Details
    loan_type = Column(SQLEnum(LoanType), nullable=False)
    purpose = Column(Text, nullable=True)
    
    # Amount Info
    requested_amount = Column(Numeric(15, 2), nullable=False)
    approved_amount = Column(Numeric(15, 2), nullable=True)
    disbursed_amount = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(3), default="USD")
    
    # Interest & Terms
    interest_rate = Column(Numeric(5, 2), nullable=False)
    term_months = Column(Integer, nullable=False)
    repayment_frequency = Column(SQLEnum(RepaymentFrequency), default=RepaymentFrequency.MONTHLY)
    
    # Calculated Fields
    total_interest = Column(Numeric(15, 2), nullable=True)
    total_repayment = Column(Numeric(15, 2), nullable=True)  # Principal + Interest
    monthly_payment = Column(Numeric(15, 2), nullable=True)
    
    # Balance Tracking
    principal_paid = Column(Numeric(15, 2), default=0.0)
    interest_paid = Column(Numeric(15, 2), default=0.0)
    fees_paid = Column(Numeric(15, 2), default=0.0)
    total_paid = Column(Numeric(15, 2), default=0.0)
    outstanding_balance = Column(Numeric(15, 2), nullable=True)
    
    # Fees
    processing_fee = Column(Numeric(15, 2), default=0.0)
    late_fees_accrued = Column(Numeric(15, 2), default=0.0)
    
    # Status
    status = Column(SQLEnum(LoanStatus), default=LoanStatus.DRAFT, nullable=False)
    
    # Collateral
    collateral_type = Column(SQLEnum(CollateralType), nullable=True)
    collateral_description = Column(Text, nullable=True)
    collateral_value = Column(Numeric(15, 2), nullable=True)
    
    # Employment Info (for eligibility)
    employer_name = Column(String(200), nullable=True)
    monthly_income = Column(Numeric(15, 2), nullable=True)
    employment_duration_months = Column(Integer, nullable=True)
    
    # Important Dates
    application_date = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    first_payment_date = Column(Date, nullable=True)
    maturity_date = Column(Date, nullable=True)
    paid_off_at = Column(DateTime(timezone=True), nullable=True)
    
    # Review Info
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Tracking
    next_payment_date = Column(Date, nullable=True)
    payments_made = Column(Integer, default=0)
    payments_remaining = Column(Integer, nullable=True)
    days_overdue = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    account = relationship("Account", foreign_keys=[account_id])
    product = relationship("LoanProduct")
    payments = relationship("LoanPayment", back_populates="loan")
    
    def __repr__(self):
        return f"<Loan(id={self.id}, ref={self.reference_number}, status={self.status})>"


class LoanPayment(Base):
    """Individual loan payments/installments"""
    __tablename__ = "loan_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    payment_number = Column(Integer, nullable=False)  # 1, 2, 3...
    
    # Scheduled amounts
    due_date = Column(Date, nullable=False)
    scheduled_amount = Column(Numeric(15, 2), nullable=False)
    principal_component = Column(Numeric(15, 2), nullable=False)
    interest_component = Column(Numeric(15, 2), nullable=False)
    
    # Actual payment
    paid_amount = Column(Numeric(15, 2), default=0.0)
    paid_principal = Column(Numeric(15, 2), default=0.0)
    paid_interest = Column(Numeric(15, 2), default=0.0)
    late_fee = Column(Numeric(15, 2), default=0.0)
    
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.SCHEDULED)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Balance after this payment
    balance_after = Column(Numeric(15, 2), nullable=True)
    
    # Payment source
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    payment_method = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    loan = relationship("Loan", back_populates="payments")
    
    def __repr__(self):
        return f"<LoanPayment(id={self.id}, loan={self.loan_id}, payment_no={self.payment_number})>"


class LoanDocument(Base):
    """Documents submitted for loan applications"""
    __tablename__ = "loan_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    
    document_type = Column(String(50), nullable=False)  # id_proof, income_proof, etc.
    document_name = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
