from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class NotificationType(str, enum.Enum):
    """Type of notification"""
    TRANSACTION = "transaction"      # Payment, transfer, deposit alerts
    SECURITY = "security"            # Login, password change, suspicious activity
    LOAN = "loan"                    # Loan approval, payment due, disbursement
    CARD = "card"                    # Card issued, blocked, limit changes
    ACCOUNT = "account"              # Balance alerts, account updates
    MARKETING = "marketing"          # Promotions, offers
    SYSTEM = "system"                # Maintenance, updates


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel"""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    """Status of notification delivery"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class NotificationPriority(str, enum.Enum):
    """Priority level for notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Notification(Base):
    """
    Notification model for storing all user notifications.
    Supports multiple channels: SMS, Email, Push, In-App.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Notification content
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.MEDIUM, nullable=False)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Delivery status
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    
    # Related entity (optional) - for linking to transactions, loans, etc.
    related_entity_type = Column(String(50), nullable=True)  # e.g., 'transaction', 'loan', 'card'
    related_entity_id = Column(Integer, nullable=True)
    
    # Additional metadata (JSON for flexibility)
    extra_data = Column(JSON, nullable=True)  # e.g., {"amount": 1000, "currency": "USD"}
    
    # External provider reference
    external_id = Column(String(255), nullable=True)  # Twilio SID, SendGrid ID, etc.
    error_message = Column(Text, nullable=True)  # Store error if failed
    
    # Timestamps
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", backref="notifications", lazy="selectin")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, status={self.status})>"


class NotificationPreference(Base):
    """
    User preferences for notification channels and types.
    Controls what notifications users want to receive and how.
    """
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Channel preferences (enable/disable)
    sms_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    
    # Type preferences (enable/disable per type)
    transaction_alerts = Column(Boolean, default=True, nullable=False)
    security_alerts = Column(Boolean, default=True, nullable=False)  # Cannot be disabled for critical
    loan_alerts = Column(Boolean, default=True, nullable=False)
    card_alerts = Column(Boolean, default=True, nullable=False)
    account_alerts = Column(Boolean, default=True, nullable=False)
    marketing_alerts = Column(Boolean, default=False, nullable=False)  # Opt-in by default
    
    # Quiet hours (optional)
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_start = Column(String(5), nullable=True)  # e.g., "22:00"
    quiet_hours_end = Column(String(5), nullable=True)    # e.g., "08:00"
    
    # Thresholds
    transaction_alert_threshold = Column(Integer, default=0, nullable=False)  # Alert for amounts above this
    low_balance_threshold = Column(Integer, default=100, nullable=False)  # Alert when balance drops below
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", backref="notification_preferences", lazy="selectin")

    def __repr__(self):
        return f"<NotificationPreference(id={self.id}, user_id={self.user_id})>"
