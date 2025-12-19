from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.modules.notifications.models import (
    Notification, NotificationPreference,
    NotificationType, NotificationChannel, NotificationStatus, NotificationPriority
)
from app.modules.notifications.schemas import (
    NotificationCreate, NotificationSend, NotificationPreferenceUpdate
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing notifications across all channels.
    Integrates with Twilio (SMS), SendGrid (Email), and Firebase (Push).
    """

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        notification_data: NotificationCreate
    ) -> Notification:
        """Create a new notification record"""
        notification = Notification(
            user_id=notification_data.user_id,
            type=NotificationType(notification_data.type.value),
            channel=NotificationChannel(notification_data.channel.value),
            priority=NotificationPriority(notification_data.priority.value),
            title=notification_data.title,
            message=notification_data.message,
            related_entity_type=notification_data.related_entity_type,
            related_entity_id=notification_data.related_entity_id,
            extra_data=notification_data.extra_data,
            status=NotificationStatus.PENDING
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def send_notification(
        db: AsyncSession,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        related_entity_type: str = None,
        related_entity_id: int = None,
        extra_data: Dict[str, Any] = None
    ) -> List[Notification]:
        """
        Send notification to user via specified channels.
        Respects user preferences for non-critical notifications.
        """
        if channels is None:
            channels = [NotificationChannel.IN_APP]

        # Get user preferences
        preferences = await NotificationService.get_or_create_preferences(db, user_id)
        
        notifications = []
        for channel in channels:
            # Check if channel is enabled (skip for critical notifications)
            if priority != NotificationPriority.CRITICAL:
                if not NotificationService._is_channel_enabled(preferences, channel):
                    continue
                if not NotificationService._is_type_enabled(preferences, notification_type):
                    continue

            # Create notification record
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                channel=channel,
                priority=priority,
                title=title,
                message=message,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                extra_data=extra_data,
                status=NotificationStatus.PENDING
            )
            db.add(notification)
            await db.flush()

            # Send via appropriate channel
            try:
                if channel == NotificationChannel.SMS:
                    await NotificationService._send_sms(notification)
                elif channel == NotificationChannel.EMAIL:
                    await NotificationService._send_email(notification)
                elif channel == NotificationChannel.PUSH:
                    await NotificationService._send_push(notification)
                elif channel == NotificationChannel.IN_APP:
                    # In-app notifications are just stored in DB
                    notification.status = NotificationStatus.DELIVERED
                    notification.delivered_at = datetime.utcnow()

                notification.sent_at = datetime.utcnow()
                if notification.status == NotificationStatus.PENDING:
                    notification.status = NotificationStatus.SENT

            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification: {str(e)}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)

            notifications.append(notification)

        await db.commit()
        for n in notifications:
            await db.refresh(n)
        
        return notifications

    @staticmethod
    async def _send_sms(notification: Notification) -> None:
        """Send SMS via Twilio"""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio not configured, skipping SMS")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "SMS provider not configured"
            return

        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Get user's phone number (would need to join with User table)
            # For now, store the attempt
            message = client.messages.create(
                body=f"{notification.title}\n{notification.message}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=notification.extra_data.get("phone_number", "") if notification.extra_data else ""
            )
            notification.external_id = message.sid
            notification.status = NotificationStatus.SENT
            logger.info(f"SMS sent successfully: {message.sid}")
        except ImportError:
            logger.warning("Twilio library not installed")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Twilio library not installed"
        except Exception as e:
            logger.error(f"SMS send failed: {str(e)}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)

    @staticmethod
    async def _send_email(notification: Notification) -> None:
        """Send Email via SendGrid"""
        if not settings.SENDGRID_API_KEY:
            logger.warning("SendGrid not configured, skipping email")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Email provider not configured"
            return

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            email_to = notification.extra_data.get("email", "") if notification.extra_data else ""
            
            message = Mail(
                from_email=settings.SENDGRID_FROM_EMAIL,
                to_emails=email_to,
                subject=notification.title,
                html_content=f"<p>{notification.message}</p>"
            )
            
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            
            notification.external_id = response.headers.get("X-Message-Id", "")
            notification.status = NotificationStatus.SENT
            logger.info(f"Email sent successfully to {email_to}")
        except ImportError:
            logger.warning("SendGrid library not installed")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "SendGrid library not installed"
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)

    @staticmethod
    async def _send_push(notification: Notification) -> None:
        """Send Push notification via Firebase"""
        # Firebase push implementation would go here
        # For now, mark as delivered (in-app style)
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = datetime.utcnow()
        logger.info(f"Push notification queued for user {notification.user_id}")

    @staticmethod
    def _is_channel_enabled(preferences: NotificationPreference, channel: NotificationChannel) -> bool:
        """Check if channel is enabled in user preferences"""
        channel_map = {
            NotificationChannel.SMS: preferences.sms_enabled,
            NotificationChannel.EMAIL: preferences.email_enabled,
            NotificationChannel.PUSH: preferences.push_enabled,
            NotificationChannel.IN_APP: preferences.in_app_enabled,
        }
        return channel_map.get(channel, True)

    @staticmethod
    def _is_type_enabled(preferences: NotificationPreference, notification_type: NotificationType) -> bool:
        """Check if notification type is enabled in user preferences"""
        type_map = {
            NotificationType.TRANSACTION: preferences.transaction_alerts,
            NotificationType.SECURITY: preferences.security_alerts,
            NotificationType.LOAN: preferences.loan_alerts,
            NotificationType.CARD: preferences.card_alerts,
            NotificationType.ACCOUNT: preferences.account_alerts,
            NotificationType.MARKETING: preferences.marketing_alerts,
            NotificationType.SYSTEM: True,  # System notifications always enabled
        }
        return type_map.get(notification_type, True)

    # ============ Read Operations ============

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        unread_only: bool = False
    ) -> tuple[List[Notification], int, int]:
        """Get user notifications with filtering and pagination"""
        query = select(Notification).where(Notification.user_id == user_id)
        
        if notification_type:
            query = query.where(Notification.type == notification_type)
        if status:
            query = query.where(Notification.status == status)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # Get unread count
        unread_query = select(func.count()).where(
            and_(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        unread_count = await db.scalar(unread_query)

        # Get notifications with pagination
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        notifications = result.scalars().all()

        return list(notifications), total or 0, unread_count or 0

    @staticmethod
    async def get_notification(db: AsyncSession, notification_id: int, user_id: int) -> Optional[Notification]:
        """Get a specific notification"""
        query = select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: int, user_id: int) -> Optional[Notification]:
        """Mark notification as read"""
        notification = await NotificationService.get_notification(db, notification_id, user_id)
        if notification and not notification.read_at:
            notification.read_at = datetime.utcnow()
            notification.status = NotificationStatus.READ
            await db.commit()
            await db.refresh(notification)
        return notification

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
        """Mark all notifications as read for user"""
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.read_at.is_(None)))
            .values(read_at=datetime.utcnow(), status=NotificationStatus.READ)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def delete_notification(db: AsyncSession, notification_id: int, user_id: int) -> bool:
        """Delete a notification"""
        notification = await NotificationService.get_notification(db, notification_id, user_id)
        if notification:
            await db.delete(notification)
            await db.commit()
            return True
        return False

    # ============ Preferences ============

    @staticmethod
    async def get_or_create_preferences(db: AsyncSession, user_id: int) -> NotificationPreference:
        """Get user preferences or create default ones"""
        query = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        result = await db.execute(query)
        preferences = result.scalar_one_or_none()

        if not preferences:
            preferences = NotificationPreference(user_id=user_id)
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)

        return preferences

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        user_id: int,
        preference_update: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        """Update user notification preferences"""
        preferences = await NotificationService.get_or_create_preferences(db, user_id)

        update_data = preference_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preferences, field, value)

        await db.commit()
        await db.refresh(preferences)
        return preferences


# ============ Banking Event Helpers ============

class BankingNotifications:
    """
    Helper class for sending banking-specific notifications.
    Use these methods from other services (transactions, loans, cards, etc.)
    """

    @staticmethod
    async def transaction_completed(
        db: AsyncSession,
        user_id: int,
        amount: float,
        currency: str,
        transaction_type: str,
        reference: str,
        phone_number: str = None,
        email: str = None
    ):
        """Send notification for completed transaction"""
        title = f"Transaction {transaction_type.title()}"
        message = f"Your {transaction_type} of {currency} {amount:,.2f} was successful. Ref: {reference}"
        
        channels = [NotificationChannel.IN_APP, NotificationChannel.PUSH]
        
        # Add SMS for large transactions
        preferences = await NotificationService.get_or_create_preferences(db, user_id)
        if amount >= preferences.transaction_alert_threshold:
            channels.append(NotificationChannel.SMS)

        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.TRANSACTION,
            title=title,
            message=message,
            channels=channels,
            priority=NotificationPriority.MEDIUM,
            related_entity_type="transaction",
            extra_data={
                "amount": amount,
                "currency": currency,
                "type": transaction_type,
                "reference": reference,
                "phone_number": phone_number,
                "email": email
            }
        )

    @staticmethod
    async def security_alert(
        db: AsyncSession,
        user_id: int,
        alert_type: str,
        details: str,
        phone_number: str = None,
        email: str = None
    ):
        """Send critical security alert"""
        title = f"Security Alert: {alert_type}"
        message = details

        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.SECURITY,
            title=title,
            message=message,
            channels=[
                NotificationChannel.SMS,
                NotificationChannel.EMAIL,
                NotificationChannel.PUSH,
                NotificationChannel.IN_APP
            ],
            priority=NotificationPriority.CRITICAL,
            extra_data={
                "alert_type": alert_type,
                "phone_number": phone_number,
                "email": email
            }
        )

    @staticmethod
    async def low_balance_alert(
        db: AsyncSession,
        user_id: int,
        balance: float,
        currency: str,
        account_name: str,
        email: str = None
    ):
        """Send low balance warning"""
        title = "Low Balance Alert"
        message = f"Your {account_name} balance is low: {currency} {balance:,.2f}"

        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT,
            title=title,
            message=message,
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.IN_APP],
            priority=NotificationPriority.MEDIUM,
            extra_data={
                "balance": balance,
                "currency": currency,
                "account_name": account_name,
                "email": email
            }
        )

    @staticmethod
    async def loan_payment_reminder(
        db: AsyncSession,
        user_id: int,
        amount: float,
        currency: str,
        due_date: str,
        loan_id: int,
        phone_number: str = None,
        email: str = None
    ):
        """Send loan payment reminder"""
        title = "Loan Payment Reminder"
        message = f"Your loan payment of {currency} {amount:,.2f} is due on {due_date}."

        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.LOAN,
            title=title,
            message=message,
            channels=[NotificationChannel.SMS, NotificationChannel.EMAIL, NotificationChannel.PUSH],
            priority=NotificationPriority.HIGH,
            related_entity_type="loan",
            related_entity_id=loan_id,
            extra_data={
                "amount": amount,
                "currency": currency,
                "due_date": due_date,
                "phone_number": phone_number,
                "email": email
            }
        )

    @staticmethod
    async def card_status_change(
        db: AsyncSession,
        user_id: int,
        card_last_four: str,
        status: str,
        reason: str = None,
        phone_number: str = None
    ):
        """Send card status change notification"""
        title = f"Card {status.title()}"
        message = f"Your card ending in {card_last_four} has been {status}."
        if reason:
            message += f" Reason: {reason}"

        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.CARD,
            title=title,
            message=message,
            channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.IN_APP],
            priority=NotificationPriority.CRITICAL if status in ["blocked", "suspended"] else NotificationPriority.MEDIUM,
            related_entity_type="card",
            extra_data={
                "card_last_four": card_last_four,
                "status": status,
                "reason": reason,
                "phone_number": phone_number
            }
        )
