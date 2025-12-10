from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime, date
from enum import Enum


# Enums
class SourceOfFundsEnum(str, Enum):
    EMPLOYMENT = "employment"
    BUSINESS = "business"
    INVESTMENTS = "investments"
    INHERITANCE = "inheritance"
    OTHER = "other"


class MonthlyIncomeRangeEnum(str, Enum):
    RANGE_0_1000 = "0-1000"
    RANGE_1001_5000 = "1001-5000"
    RANGE_5001_10000 = "5001-10000"
    RANGE_10001_20000 = "10001-20000"
    RANGE_20000_PLUS = "20000+"


class AccountStatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class KYCStatusEnum(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TwoFactorMethodEnum(str, Enum):
    NONE = "none"
    SMS = "sms"
    AUTHENTICATOR = "authenticator"


class GovernmentIDTypeEnum(str, Enum):
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"


class ProofOfAddressTypeEnum(str, Enum):
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    TAX_BILL = "tax_bill"
    RENTAL_AGREEMENT = "rental_agreement"


# User Registration
class UserRegistrationRequest(BaseModel):
    """Complete user registration request"""
    # Authentication
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8)
    
    # Personal Information
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    nationality: str = Field(..., min_length=2, max_length=100)
    country_of_residence: str = Field(..., min_length=2, max_length=100)
    
    # Address
    street_address: str = Field(..., min_length=5, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field(..., min_length=2, max_length=100)
    
    # Financial Profile
    occupation: str = Field(..., min_length=2, max_length=100)
    source_of_funds: SourceOfFundsEnum
    monthly_income_range: MonthlyIncomeRangeEnum
    tax_identification_number: Optional[str] = Field(None, max_length=50)
    
    # Compliance
    accepted_terms: bool = True
    accepted_privacy_policy: bool = True
    marketing_consent: bool = False
    
    @validator('date_of_birth')
    def validate_age(cls, v):
        """Ensure user is at least 18 years old"""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('You must be at least 18 years old to register')
        if age > 120:
            raise ValueError('Invalid date of birth')
        return v
    
    @validator('accepted_terms', 'accepted_privacy_policy')
    def validate_acceptance(cls, v):
        """Ensure terms and privacy policy are accepted"""
        if not v:
            raise ValueError('You must accept the terms and privacy policy')
        return v


# User Login
class UserLoginRequest(BaseModel):
    """User login request"""
    email_or_phone: str
    password: str
    two_factor_code: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# User Profile
class UserProfileResponse(BaseModel):
    """Complete user profile response"""
    id: int
    email: str
    phone_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    nationality: str
    country_of_residence: str
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str
    occupation: str
    source_of_funds: str
    monthly_income_range: str
    tax_identification_number: Optional[str]
    kyc_status: str
    account_status: str
    email_verified: bool
    phone_verified: bool
    two_factor_enabled: bool
    two_factor_method: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Update user profile"""
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    street_address: Optional[str] = Field(None, min_length=5, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=3, max_length=20)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    occupation: Optional[str] = Field(None, min_length=2, max_length=100)


# KYC Schemas
class KYCSubmissionRequest(BaseModel):
    """KYC document submission request"""
    government_id_type: GovernmentIDTypeEnum
    government_id_number: str = Field(..., min_length=5, max_length=100)
    document_issue_date: date
    document_expiry_date: Optional[date] = None
    proof_of_address_type: ProofOfAddressTypeEnum
    
    @validator('document_expiry_date')
    def validate_expiry(cls, v, values):
        """Ensure document is not expired"""
        if v and v < date.today():
            raise ValueError('Document has expired')
        if v and 'document_issue_date' in values:
            if v <= values['document_issue_date']:
                raise ValueError('Expiry date must be after issue date')
        return v


class KYCStatusResponse(BaseModel):
    """KYC verification status response"""
    kyc_status: str
    kyc_rejection_reason: Optional[str]
    kyc_verified_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class KYCDocumentResponse(BaseModel):
    """KYC document response"""
    id: int
    user_id: int
    government_id_type: str
    government_id_number: str
    status: str
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Verification Schemas
class EmailVerificationRequest(BaseModel):
    """Email verification request"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class PhoneVerificationRequest(BaseModel):
    """Phone verification request"""
    phone_number: str
    otp: str = Field(..., min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    """Resend verification code"""
    email_or_phone: str
    verification_type: str = Field(..., pattern="^(email|phone)$")


# Password Management
class PasswordResetRequest(BaseModel):
    """Initiate password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token"""
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChangeRequest(BaseModel):
    """Change password (authenticated)"""
    old_password: str
    new_password: str = Field(..., min_length=8)


# 2FA Schemas
class TwoFactorSetupResponse(BaseModel):
    """2FA setup response"""
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class TwoFactorEnableRequest(BaseModel):
    """Enable 2FA"""
    method: TwoFactorMethodEnum
    verification_code: str = Field(..., min_length=6, max_length=6)


class TwoFactorVerifyRequest(BaseModel):
    """Verify 2FA code"""
    code: str = Field(..., min_length=6, max_length=6)


# Account Closure
class AccountClosureRequest(BaseModel):
    """Request account closure"""
    reason: str = Field(..., min_length=10, max_length=500)
    password: str

