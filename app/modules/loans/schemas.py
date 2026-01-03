from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from enum import Enum


# ============================================================
# Enums (matching models.py)
# ============================================================

class LoanType(str, Enum):
    PERSONAL = "personal"
    AUTO = "auto"
    HOME = "home"
    EDUCATION = "education"
    BUSINESS = "business"
    EMERGENCY = "emergency"
    SALARY_ADVANCE = "salary_advance"
    OVERDRAFT = "overdraft"


class LoanStatus(str, Enum):
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


class RepaymentFrequency(str, Enum):
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class PaymentStatus(str, Enum):
    SCHEDULED = "scheduled"
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    WAIVED = "waived"


class CollateralType(str, Enum):
    PROPERTY = "property"
    VEHICLE = "vehicle"
    SAVINGS = "savings"
    STOCKS = "stocks"
    GUARANTOR = "guarantor"
    SALARY = "salary"
    NONE = "none"


# ============================================================
# Loan Product Schemas
# ============================================================

class LoanProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    loan_type: LoanType
    description: Optional[str] = None


class LoanProductCreate(LoanProductBase):
    min_interest_rate: Decimal = Field(..., ge=0, le=100)
    max_interest_rate: Decimal = Field(..., ge=0, le=100)
    default_interest_rate: Decimal = Field(..., ge=0, le=100)
    min_amount: Decimal = Field(..., gt=0)
    max_amount: Decimal = Field(..., gt=0)
    min_term_months: int = Field(..., ge=1)
    max_term_months: int = Field(..., ge=1)
    processing_fee_percentage: Decimal = Field(default=0.0, ge=0, le=1)
    processing_fee_flat: Decimal = Field(default=0.0, ge=0)
    late_payment_fee: Decimal = Field(default=0.0, ge=0)
    requires_collateral: bool = False
    repayment_frequency: RepaymentFrequency = RepaymentFrequency.MONTHLY
    grace_period_days: int = Field(default=0, ge=0)
    
    @validator('max_interest_rate')
    def max_greater_than_min_rate(cls, v, values):
        if 'min_interest_rate' in values and v < values['min_interest_rate']:
            raise ValueError('max_interest_rate must be >= min_interest_rate')
        return v
    
    @validator('max_amount')
    def max_greater_than_min_amount(cls, v, values):
        if 'min_amount' in values and v < values['min_amount']:
            raise ValueError('max_amount must be >= min_amount')
        return v


class LoanProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_interest_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None


class LoanProductResponse(LoanProductBase):
    id: int
    min_interest_rate: Decimal
    max_interest_rate: Decimal
    default_interest_rate: Decimal
    min_amount: Decimal
    max_amount: Decimal
    min_term_months: int
    max_term_months: int
    processing_fee_percentage: Decimal
    processing_fee_flat: Decimal
    late_payment_fee: Decimal
    requires_collateral: bool
    repayment_frequency: RepaymentFrequency
    grace_period_days: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# Loan Application Schemas
# ============================================================

class LoanApplicationRequest(BaseModel):
    """Initial loan application"""
    product_id: int
    account_id: int = Field(..., description="Account for disbursement")
    requested_amount: Decimal = Field(..., gt=0)
    term_months: int = Field(..., ge=1)
    purpose: Optional[str] = Field(None, max_length=500)
    
    # Employment info
    employer_name: Optional[str] = None
    monthly_income: Optional[Decimal] = None
    employment_duration_months: Optional[int] = None
    
    # Collateral (if required)
    collateral_type: Optional[CollateralType] = None
    collateral_description: Optional[str] = None
    collateral_value: Optional[Decimal] = None


class LoanSubmitRequest(BaseModel):
    """Submit a draft loan for review"""
    loan_id: int
    

class LoanApprovalRequest(BaseModel):
    """Admin approval of loan"""
    loan_id: int
    approved_amount: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(..., ge=0, le=100)
    approval_notes: Optional[str] = None


class LoanRejectionRequest(BaseModel):
    """Admin rejection of loan"""
    loan_id: int
    rejection_reason: str = Field(..., min_length=10, max_length=500)


class LoanDisbursementRequest(BaseModel):
    """Disburse approved loan"""
    loan_id: int


# ============================================================
# Loan Response Schemas
# ============================================================

class LoanPaymentScheduleItem(BaseModel):
    payment_number: int
    due_date: date
    scheduled_amount: Decimal
    principal_component: Decimal
    interest_component: Decimal
    balance_after: Decimal
    status: PaymentStatus
    
    class Config:
        from_attributes = True


class LoanResponse(BaseModel):
    id: int
    reference_number: str
    user_id: int
    account_id: Optional[int]
    product_id: int
    
    loan_type: LoanType
    purpose: Optional[str]
    
    # Amounts
    requested_amount: Decimal
    approved_amount: Optional[Decimal]
    disbursed_amount: Optional[Decimal]
    currency: str
    
    # Terms
    interest_rate: Decimal
    term_months: int
    repayment_frequency: RepaymentFrequency
    
    # Calculated
    total_interest: Optional[Decimal]
    total_repayment: Optional[Decimal]
    monthly_payment: Optional[Decimal]
    
    # Balance
    principal_paid: Decimal
    interest_paid: Decimal
    total_paid: Decimal
    outstanding_balance: Optional[Decimal]
    
    # Fees
    processing_fee: Decimal
    late_fees_accrued: Decimal
    
    # Status
    status: LoanStatus
    
    # Dates
    application_date: datetime
    approved_at: Optional[datetime]
    disbursed_at: Optional[datetime]
    first_payment_date: Optional[date]
    maturity_date: Optional[date]
    next_payment_date: Optional[date]
    
    # Progress
    payments_made: int
    payments_remaining: Optional[int]
    days_overdue: int
    
    class Config:
        from_attributes = True


class LoanListResponse(BaseModel):
    loans: List[LoanResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LoanDetailResponse(LoanResponse):
    """Detailed loan response with payment schedule"""
    collateral_type: Optional[CollateralType]
    collateral_description: Optional[str]
    collateral_value: Optional[Decimal]
    employer_name: Optional[str]
    monthly_income: Optional[Decimal]
    rejection_reason: Optional[str]
    approval_notes: Optional[str]
    payment_schedule: List[LoanPaymentScheduleItem] = []


# ============================================================
# Loan Repayment Schemas
# ============================================================

class LoanRepaymentRequest(BaseModel):
    """Make a loan payment"""
    loan_id: int
    amount: Decimal = Field(..., gt=0)
    source_account_id: int
    payment_number: Optional[int] = None  # Specific payment, or next due


class LoanEarlyPayoffRequest(BaseModel):
    """Pay off entire loan early"""
    loan_id: int
    source_account_id: int


class LoanRepaymentResponse(BaseModel):
    payment_id: int
    loan_id: int
    amount_paid: Decimal
    principal_paid: Decimal
    interest_paid: Decimal
    late_fee_paid: Decimal
    new_balance: Decimal
    payment_date: datetime
    loan_status: LoanStatus
    payments_remaining: int
    
    class Config:
        from_attributes = True


# ============================================================
# Loan Eligibility
# ============================================================

class LoanEligibilityRequest(BaseModel):
    product_id: int
    requested_amount: Decimal
    term_months: int
    monthly_income: Optional[Decimal] = None


class LoanEligibilityResponse(BaseModel):
    eligible: bool
    max_eligible_amount: Decimal
    recommended_term_months: int
    estimated_interest_rate: Decimal
    estimated_monthly_payment: Decimal
    estimated_total_repayment: Decimal
    reasons: List[str] = []  # If not eligible, why


# ============================================================
# Loan Calculator
# ============================================================

class LoanCalculatorRequest(BaseModel):
    principal: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(..., ge=0, le=100)  # Annual %
    term_months: int = Field(..., ge=1, le=360)
    repayment_frequency: RepaymentFrequency = RepaymentFrequency.MONTHLY


class LoanCalculatorResponse(BaseModel):
    principal: Decimal
    interest_rate: Decimal
    term_months: int
    monthly_payment: Decimal
    total_interest: Decimal
    total_repayment: Decimal
    amortization_schedule: List[LoanPaymentScheduleItem]


# ============================================================
# Loan Summary / Dashboard
# ============================================================

class LoanSummary(BaseModel):
    total_loans: int
    active_loans: int
    total_borrowed: Decimal
    total_outstanding: Decimal
    total_paid: Decimal
    next_payment_amount: Optional[Decimal]
    next_payment_date: Optional[date]
    overdue_amount: Decimal
    loans_by_status: dict
