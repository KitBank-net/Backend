from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class NotificationTypeEnum(str, Enum):
    TRANSACTION = "transaction"
    SECURITY = "security"
    LOAN = "loan"
    CARD = "card"
    ACCOUNT = "account"
    MARKETING = "marketing"
    SYSTEM = "system"


class NotificationChannelEnum(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatusEnum(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class NotificationPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============ Notification Schemas ============

class NotificationBase(BaseModel):
    """Base notification fields"""
    type: NotificationTypeEnum
    channel: NotificationChannelEnum
    priority: NotificationPriorityEnum = NotificationPriorityEnum.MEDIUM
    title: str = Field(..., max_length=255)
    message: str


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    user_id: int
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None


class NotificationSend(BaseModel):
    """Schema for sending a notification to current user"""
    type: NotificationTypeEnum
    title: str = Field(..., max_length=255)
    message: str
    priority: NotificationPriorityEnum = NotificationPriorityEnum.MEDIUM
    channels: List[NotificationChannelEnum] = [NotificationChannelEnum.IN_APP]
    extra_data: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    """Response schema for notification"""
    id: int
    user_id: int
    type: NotificationTypeEnum
    channel: NotificationChannelEnum
    priority: NotificationPriorityEnum
    title: str
    message: str
    status: NotificationStatusEnum
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response for paginated notification list"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    limit: int


# ============ Notification Preference Schemas ============

class NotificationPreferenceBase(BaseModel):
    """Base preference fields"""
    # Channel preferences
    sms_enabled: bool = True
    email_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    # Type preferences
    transaction_alerts: bool = True
    security_alerts: bool = True
    loan_alerts: bool = True
    card_alerts: bool = True
    account_alerts: bool = True
    marketing_alerts: bool = False
    
    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None    # "08:00"
    
    # Thresholds
    transaction_alert_threshold: int = 0
    low_balance_threshold: int = 100


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating preferences (all optional)"""
    sms_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    
    transaction_alerts: Optional[bool] = None
    security_alerts: Optional[bool] = None
    loan_alerts: Optional[bool] = None
    card_alerts: Optional[bool] = None
    account_alerts: Optional[bool] = None
    marketing_alerts: Optional[bool] = None
    
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    transaction_alert_threshold: Optional[int] = None
    low_balance_threshold: Optional[int] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    """Response schema for preferences"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Bulk Notification Schemas ============

class BulkNotificationCreate(BaseModel):
    """Schema for sending notifications to multiple users"""
    user_ids: List[int]
    type: NotificationTypeEnum
    title: str = Field(..., max_length=255)
    message: str
    priority: NotificationPriorityEnum = NotificationPriorityEnum.MEDIUM
    channels: List[NotificationChannelEnum] = [NotificationChannelEnum.IN_APP]


class BulkNotificationResponse(BaseModel):
    """Response for bulk notification creation"""
    total_users: int
    successful: int
    failed: int
    notification_ids: List[int]
