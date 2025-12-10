from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums
class LoginMethodEnum(str, Enum):
    PASSWORD = "password"
    TWO_FA = "2fa"
    BIOMETRIC = "biometric"
    SOCIAL = "social"


class DeviceTypeEnum(str, Enum):
    WEB = "web"
    IOS = "ios"
    ANDROID = "android"
    DESKTOP = "desktop"


class AlertTypeEnum(str, Enum):
    FAILED_LOGIN = "failed_login"
    SUSPICIOUS_LOGIN = "suspicious_login"
    PASSWORD_CHANGE = "password_change"
    KYC_UPDATE = "kyc_update"
    LARGE_TRANSFER = "large_transfer"
    NEW_DEVICE = "new_device"
    CARD_BLOCKED = "card_blocked"
    ACCOUNT_LOCKED = "account_locked"


class SeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Login History
class LoginHistoryResponse(BaseModel):
    """Login history entry"""
    id: int
    login_method: str
    device_type: str
    device_name: Optional[str]
    browser: Optional[str]
    ip_address: str
    country: Optional[str]
    city: Optional[str]
    login_successful: bool
    failure_reason: Optional[str]
    attempted_at: datetime
    
    class Config:
        from_attributes = True


# Trusted Devices
class TrustedDeviceResponse(BaseModel):
    """Trusted device information"""
    id: int
    device_name: str
    device_type: str
    trust_level: str
    is_trusted: bool
    last_used: datetime
    trusted_since: datetime
    
    class Config:
        from_attributes = True


# Security Alerts
class SecurityAlertResponse(BaseModel):
    """Security alert"""
    id: int
    alert_type: str
    severity: str
    description: str
    ip_address: Optional[str]
    location: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResolveAlertRequest(BaseModel):
    """Resolve security alert"""
    resolution_notes: str = Field(..., min_length=10, max_length=500)


# Suspicious Activity
class ReportSuspiciousRequest(BaseModel):
    """Report suspicious activity"""
    description: str = Field(..., min_length=20, max_length=1000)
    incident_type: str
