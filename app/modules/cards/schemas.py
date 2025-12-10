from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# Enums
class CardTypeEnum(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"


class CardStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CardTierEnum(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    PLATINUM = "platinum"


# Card Creation
class VirtualCardCreateRequest(BaseModel):
    """Request to create a new virtual card"""
    account_id: int
    card_type: CardTypeEnum = CardTypeEnum.VISA
    card_tier: CardTierEnum = CardTierEnum.STANDARD
    daily_spend_limit: Optional[Decimal] = Field(default=Decimal("5000.00"), ge=0, le=50000)
    monthly_spend_limit: Optional[Decimal] = Field(default=Decimal("15000.00"), ge=0, le=200000)


class VirtualCardResponse(BaseModel):
    """Virtual card response with masked details"""
    id: int
    account_id: int
    card_number_masked: str  # e.g., "************1234"
    expiry_month: int
    expiry_year: int
    card_holder_name: str
    card_type: str
    card_status: str
    card_tier: str
    daily_spend_limit: Decimal
    monthly_spend_limit: Decimal
    transaction_limit: Decimal
    atm_withdrawal_limit: Decimal
    international_use: bool
    online_purchases: bool
    contactless_payments: bool
    card_issue_date: date
    card_expiry_date: date
    created_at: datetime
    
    class Config:
        from_attributes = True


class VirtualCardFullResponse(BaseModel):
    """Full card details (only shown once at creation)"""
    id: int
    account_id: int
    card_number: str  # Full card number (only shown at creation)
    expiry_month: int
    expiry_year: int
    cvv: str  # CVV (only shown at creation)
    card_holder_name: str
    card_type: str
    card_tier: str
    daily_spend_limit: Decimal
    monthly_spend_limit: Decimal


# Card Controls
class CardControlsUpdate(BaseModel):
    """Update card controls"""
    international_use: Optional[bool] = None
    online_purchases: Optional[bool] = None
    contactless_payments: Optional[bool] = None


class CardLimitsUpdate(BaseModel):
    """Update card spending limits"""
    daily_spend_limit: Optional[Decimal] = Field(None, ge=0, le=50000)
    monthly_spend_limit: Optional[Decimal] = Field(None, ge=0, le=200000)
    transaction_limit: Optional[Decimal] = Field(None, ge=0, le=10000)
    atm_withdrawal_limit: Optional[Decimal] = Field(None, ge=0, le=5000)


class CardBlockRequest(BaseModel):
    """Block or unblock card"""
    block: bool
    reason: Optional[str] = Field(None, max_length=500)


class CardPINSetRequest(BaseModel):
    """Set or change card PIN"""
    pin: str = Field(..., min_length=4, max_length=6, pattern="^[0-9]+$")
    confirm_pin: str = Field(..., min_length=4, max_length=6, pattern="^[0-9]+$")
    
    @validator('confirm_pin')
    def pins_match(cls, v, values):
        if 'pin' in values and v != values['pin']:
            raise ValueError('PINs do not match')
        return v


class CardCVVResponse(BaseModel):
    """CVV response (temporary)"""
    cvv: str
    expires_in_seconds: int = 300  # CVV visible for 5 minutes


class CardCancellationRequest(BaseModel):
    """Cancel virtual card"""
    reason: str = Field(..., min_length=10, max_length=500)


class CardDisputeRequest(BaseModel):
    """Report disputed transaction"""
    transaction_id: int
    dispute_reason: str = Field(..., min_length=20, max_length=1000)
    dispute_amount: Decimal = Field(..., gt=0)


class CardTempLockRequest(BaseModel):
    """Temporarily lock card"""
    lock_duration_hours: int = Field(default=24, ge=1, le=168)  # Max 7 days
    reason: Optional[str] = Field(None, max_length=500)


class CardSecurityStatusResponse(BaseModel):
    """Card security status"""
    card_id: int
    card_status: str
    fraud_alert_level: str
    pin_locked: bool
    cvv_locked: bool
    temp_lock_active: bool
    temp_lock_expires_at: Optional[datetime]
    last_used_date: Optional[datetime]
    
    class Config:
        from_attributes = True


class CardBalanceResponse(BaseModel):
    """Card available balance"""
    card_id: int
    account_id: int
    available_balance: Decimal
    daily_remaining: Decimal
    monthly_remaining: Decimal
