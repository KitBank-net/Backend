from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum


# ============================================================
# Enums
# ============================================================

class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"
    SUPPORT = "support"
    COMPLIANCE = "compliance"
    AUDITOR = "auditor"


# ============================================================
# Admin User Schemas
# ============================================================

class AdminUserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = None
    role: AdminRole = AdminRole.SUPPORT


class AdminUserCreate(AdminUserBase):
    password: str = Field(..., min_length=8)
    user_id: Optional[int] = None  # Link to existing user


class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    custom_permissions: Optional[str] = None


class AdminUserResponse(AdminUserBase):
    id: int
    user_id: Optional[int]
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp_code: Optional[str] = None


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminUserResponse
    permissions: List[str]


# ============================================================
# Audit Log Schemas
# ============================================================

class AuditLogResponse(BaseModel):
    id: int
    admin_id: Optional[int]
    admin_email: Optional[str]
    ip_address: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[int]
    description: Optional[str]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogFilter(BaseModel):
    admin_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    success: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ============================================================
# System Settings Schemas
# ============================================================

class SystemSettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str]
    value_type: str
    category: str
    description: Optional[str]
    is_readonly: bool
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SystemSettingUpdate(BaseModel):
    value: str


# ============================================================
# Dashboard / Statistics
# ============================================================

class DashboardStats(BaseModel):
    # Users
    total_users: int
    active_users: int
    pending_kyc: int
    new_users_today: int
    new_users_this_week: int
    
    # Accounts
    total_accounts: int
    total_balance: Decimal
    
    # Transactions
    transactions_today: int
    transactions_this_week: int
    transaction_volume_today: Decimal
    transaction_volume_this_week: Decimal
    
    # Loans
    total_loans: int
    pending_loan_applications: int
    active_loans: int
    total_loan_amount: Decimal
    overdue_loans: int
    
    # Cards
    total_cards: int
    active_cards: int


class UserManagementResponse(BaseModel):
    id: int
    email: str
    phone_number: str
    first_name: str
    last_name: str
    kyc_status: str
    account_status: str
    accounts_count: int
    total_balance: Decimal
    created_at: datetime
    last_login_at: Optional[datetime]


class UserManagementListResponse(BaseModel):
    users: List[UserManagementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# KYC Management
# ============================================================

class KYCReviewRequest(BaseModel):
    user_id: int
    approved: bool
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class KYCPendingResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    phone_number: str
    nationality: str
    submitted_at: Optional[datetime]
    documents: List[str]


# ============================================================
# Transaction Management
# ============================================================

class TransactionReversalRequest(BaseModel):
    transaction_id: int
    reason: str = Field(..., min_length=10, max_length=500)


class TransactionRefundRequest(BaseModel):
    transaction_id: int
    amount: Optional[Decimal] = None  # Partial or full
    reason: str = Field(..., min_length=10, max_length=500)


# ============================================================
# Fee Management
# ============================================================

class FeeConfigCreate(BaseModel):
    transaction_type: str
    currency: str
    flat_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    percentage_fee: Decimal = Field(default=Decimal("0.00"), ge=0, le=1)
    min_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    max_fee: Optional[Decimal] = None
    min_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    max_amount: Optional[Decimal] = None


class FeeConfigUpdate(BaseModel):
    flat_fee: Optional[Decimal] = None
    percentage_fee: Optional[Decimal] = None
    min_fee: Optional[Decimal] = None
    max_fee: Optional[Decimal] = None
    is_active: Optional[bool] = None
