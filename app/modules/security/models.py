from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON, Boolean, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class LoginMethod(str, enum.Enum):
    """Login method"""
    PASSWORD = "password"
    TWO_FA = "2fa"
    BIOMETRIC = "biometric"
    SOCIAL = "social"


class DeviceType(str, enum.Enum):
    """Device type"""
    WEB = "web"
    IOS = "ios"
    ANDROID = "android"
    DESKTOP = "desktop"


class TrustLevel(str, enum.Enum):
    """Device trust level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertType(str, enum.Enum):
    """Security alert type"""
    FAILED_LOGIN = "failed_login"
    SUSPICIOUS_LOGIN = "suspicious_login"
    PASSWORD_CHANGE = "password_change"
    KYC_UPDATE = "kyc_update"
    LARGE_TRANSFER = "large_transfer"
    NEW_DEVICE = "new_device"
    CARD_BLOCKED = "card_blocked"
    ACCOUNT_LOCKED = "account_locked"


class Severity(str, enum.Enum):
    """Alert severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    NEW = "new"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class AMLCheckType(str, enum.Enum):
    """AML check type"""
    INITIAL = "initial"
    PERIODIC = "periodic"
    TRANSACTION = "transaction"
    ENHANCED = "enhanced"


class ScreeningType(str, enum.Enum):
    """Screening type"""
    PEP = "pep"  # Politically Exposed Person
    SANCTIONS = "sanctions"
    ADVERSE_MEDIA = "adverse_media"
    WATCHLIST = "watchlist"


class AMLStatus(str, enum.Enum):
    """AML check status"""
    PENDING = "pending"
    CLEARED = "cleared"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class LoginHistory(Base):
    """Login history tracking"""
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Login Details
    login_method = Column(SQLEnum(LoginMethod), nullable=False)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    device_id = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    browser = Column(String(100), nullable=True)
    browser_version = Column(String(50), nullable=True)
    os = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    
    # Location
    ip_address = Column(String(45), nullable=False)  # IPv6 compatible
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Status
    login_successful = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)
    
    # Timestamp
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class TrustedDevice(Base):
    """Trusted devices for reduced 2FA"""
    __tablename__ = "trusted_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Device Information
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)
    device_identifier = Column(String(500), unique=True, nullable=False)  # Fingerprint/unique ID
    browser_fingerprint = Column(Text, nullable=True)
    
    # Trust Settings
    trust_level = Column(SQLEnum(TrustLevel), default=TrustLevel.MEDIUM, nullable=False)
    is_trusted = Column(Boolean, default=True, nullable=False)
    trusted_since = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    mfa_required = Column(Boolean, default=False, nullable=False)
    last_used = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class SecurityAlert(Base):
    """Security events and alerts"""
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Alert Details
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(Severity), nullable=False)
    description = Column(Text, nullable=False)
    alert_metadata = Column(JSON, nullable=True)  # Additional context (renamed from metadata)
    
    # Location
    ip_address = Column(String(45), nullable=True)
    location = Column(String(255), nullable=True)
    
    # Status
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.NEW, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, nullable=True)  # Admin user ID
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class AMLCheck(Base):
    """Anti-Money Laundering checks"""
    __tablename__ = "aml_checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Check Details
    check_type = Column(SQLEnum(AMLCheckType), nullable=False)
    screening_type = Column(SQLEnum(ScreeningType), nullable=False)
    status = Column(SQLEnum(AMLStatus), nullable=False)
    
    # Results
    match_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    match_details = Column(JSON, nullable=True)
    
    # Review
    screened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by = Column(Integer, nullable=True)  # Admin user ID
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
