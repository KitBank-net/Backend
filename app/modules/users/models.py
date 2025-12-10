from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class SourceOfFunds(str, enum.Enum):
    """Source of funds enumeration"""
    EMPLOYMENT = "employment"
    BUSINESS = "business"
    INVESTMENTS = "investments"
    INHERITANCE = "inheritance"
    OTHER = "other"


class MonthlyIncomeRange(str, enum.Enum):
    """Monthly income range enumeration"""
    RANGE_0_1000 = "0-1000"
    RANGE_1001_5000 = "1001-5000"
    RANGE_5001_10000 = "5001-10000"
    RANGE_10001_20000 = "10001-20000"
    RANGE_20000_PLUS = "20000+"


class AccountStatus(str, enum.Enum):
    """Account status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class KYCStatus(str, enum.Enum):
    """KYC verification status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TwoFactorMethod(str, enum.Enum):
    """Two-factor authentication method"""
    NONE = "none"
    SMS = "sms"
    AUTHENTICATOR = "authenticator"


class User(Base):
    """User model with complete KYC and compliance fields"""
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    nationality = Column(String(100), nullable=False)
    country_of_residence = Column(String(100), nullable=False)
    
    # Address Information
    street_address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    
    # Financial Profile
    occupation = Column(String(100), nullable=False)
    source_of_funds = Column(SQLEnum(SourceOfFunds), nullable=False)
    monthly_income_range = Column(SQLEnum(MonthlyIncomeRange), nullable=False)
    tax_identification_number = Column(String(50), nullable=True)
    
    # KYC Status
    kyc_status = Column(SQLEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    kyc_rejection_reason = Column(Text, nullable=True)
    kyc_verified_at = Column(DateTime(timezone=True), nullable=True)
    kyc_reviewer_id = Column(Integer, nullable=True)
    
    # Account Status
    account_status = Column(SQLEnum(AccountStatus), default=AccountStatus.PENDING, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    
    # Two-Factor Authentication
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(SQLEnum(TwoFactorMethod), default=TwoFactorMethod.NONE, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)  # For authenticator apps
    
    # Security
    login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Compliance
    accepted_terms = Column(Boolean, default=False, nullable=False)
    accepted_privacy_policy = Column(Boolean, default=False, nullable=False)
    marketing_consent = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    accounts = relationship("Account", back_populates="user", lazy="selectin")
    kyc_documents = relationship("KYCDocument", back_populates="user", lazy="selectin")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, status={self.account_status})>"

