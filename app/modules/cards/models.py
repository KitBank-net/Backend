from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date, Boolean, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CardType(str, enum.Enum):
    """Card type/network"""
    VISA = "visa"
    MASTERCARD = "mastercard"


class CardStatus(str, enum.Enum):
    """Card status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CardTier(str, enum.Enum):
    """Card tier"""
    STANDARD = "standard"
    PREMIUM = "premium"
    PLATINUM = "platinum"


class FraudAlertLevel(str, enum.Enum):
    """Fraud alert level"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CreatedBy(str, enum.Enum):
    """Card creation source"""
    USER = "user"
    SYSTEM = "system"
    ADMIN = "admin"


class VirtualCard(Base):
    """Virtual card model with complete security features"""
    __tablename__ = "virtual_cards"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    
    # Card Details (encrypted/hashed)
    card_number_encrypted = Column(String(500), nullable=False)  # Encrypted card number
    card_hash = Column(String(255), unique=True, nullable=False, index=True)  # Hash for verification
    expiry_month = Column(Integer, nullable=False)  # 1-12
    expiry_year = Column(Integer, nullable=False)  # 4 digits
    cvv_hash = Column(String(255), nullable=False)  # Hashed CVV
    
    # Card Information
    card_type = Column(SQLEnum(CardType), nullable=False)
    card_network = Column(SQLEnum(CardType), nullable=False)  # Same as card_type for now
    card_holder_name = Column(String(200), nullable=False)
    card_status = Column(SQLEnum(CardStatus), default=CardStatus.ACTIVE, nullable=False)
    card_tier = Column(SQLEnum(CardTier), default=CardTier.STANDARD, nullable=False)
    
    # Spending Limits
    daily_spend_limit = Column(Numeric(15, 2), default=5000.00, nullable=False)
    monthly_spend_limit = Column(Numeric(15, 2), default=15000.00, nullable=False)
    transaction_limit = Column(Numeric(15, 2), default=2500.00, nullable=False)
    atm_withdrawal_limit = Column(Numeric(15, 2), default=1000.00, nullable=False)
    
    # Card Controls
    international_use = Column(Boolean, default=True, nullable=False)
    online_purchases = Column(Boolean, default=True, nullable=False)
    contactless_payments = Column(Boolean, default=True, nullable=False)
    
    # Dates
    card_issue_date = Column(Date, default=func.current_date(), nullable=False)
    card_expiry_date = Column(Date, nullable=False)  # Calculated from expiry_month/year
    activation_date = Column(DateTime(timezone=True), nullable=True)
    cancellation_date = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    last_used_date = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    pin_hash = Column(String(255), nullable=True)  # Hashed PIN
    pin_attempts = Column(Integer, default=0, nullable=False)
    pin_locked_until = Column(DateTime(timezone=True), nullable=True)
    cvv_attempts = Column(Integer, default=0, nullable=False)
    cvv_locked_until = Column(DateTime(timezone=True), nullable=True)
    temp_lock_reason = Column(Text, nullable=True)
    fraud_alert_level = Column(SQLEnum(FraudAlertLevel), default=FraudAlertLevel.NONE, nullable=False)
    
    # Metadata
    created_by = Column(SQLEnum(CreatedBy), default=CreatedBy.USER, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    account = relationship("Account", foreign_keys=[account_id])
    
    def __repr__(self):
        return f"<VirtualCard(id={self.id}, status={self.card_status}, tier={self.card_tier})>"
