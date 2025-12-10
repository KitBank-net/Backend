from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Optional

from app.modules.security.models import (
    LoginHistory, TrustedDevice, SecurityAlert, AMLCheck,
    LoginMethod, DeviceType, AlertType, Severity, AlertStatus
)
from app.modules.security import schemas
from app.modules.users.models import User


class SecurityService:
    """Service layer for security and compliance operations"""
    
    @staticmethod
    async def log_login_attempt(
        db: AsyncSession,
        user_id: int,
        login_method: LoginMethod,
        device_type: DeviceType,
        ip_address: str,
        success: bool,
        device_name: Optional[str] = None,
        browser: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> LoginHistory:
        """Log a login attempt"""
        
        log_entry = LoginHistory(
            user_id=user_id,
            login_method=login_method,
            device_type=device_type,
            device_name=device_name,
            browser=browser,
            ip_address=ip_address,
            login_successful=success,
            failure_reason=failure_reason
        )
        
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        
        return log_entry
    
    @staticmethod
    async def get_login_history(
        db: AsyncSession,
        user_id: int,
        limit: int = 50
    ) -> List[LoginHistory]:
        """Get user login history"""
        result = await db.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(desc(LoginHistory.attempted_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_trusted_devices(
        db: AsyncSession,
        user_id: int
    ) -> List[TrustedDevice]:
        """Get user's trusted devices"""
        result = await db.execute(
            select(TrustedDevice)
            .where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.is_trusted == True
                )
            )
            .order_by(desc(TrustedDevice.last_used))
        )
        return result.scalars().all()
    
    @staticmethod
    async def remove_trusted_device(
        db: AsyncSession,
        device_id: int,
        user_id: int
    ) -> bool:
        """Remove a trusted device"""
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.id == device_id,
                    TrustedDevice.user_id == user_id
                )
            )
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        await db.delete(device)
        await db.commit()
        
        return True
    
    @staticmethod
    async def get_security_alerts(
        db: AsyncSession,
        user_id: int,
        limit: int = 50
    ) -> List[SecurityAlert]:
        """Get user security alerts"""
        result = await db.execute(
            select(SecurityAlert)
            .where(SecurityAlert.user_id == user_id)
            .order_by(desc(SecurityAlert.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def create_security_alert(
        db: AsyncSession,
        user_id: int,
        alert_type: AlertType,
        severity: Severity,
        description: str,
        ip_address: Optional[str] = None,
        location: Optional[str] = None
    ) -> SecurityAlert:
        """Create a security alert"""
        
        alert = SecurityAlert(
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            location=location,
            status=AlertStatus.NEW
        )
        
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        
        return alert
    
    @staticmethod
    async def resolve_alert(
        db: AsyncSession,
        alert_id: int,
        user_id: int,
        resolution_notes: str
    ) -> SecurityAlert:
        """Resolve a security alert"""
        result = await db.execute(
            select(SecurityAlert).where(
                and_(
                    SecurityAlert.id == alert_id,
                    SecurityAlert.user_id == user_id
                )
            )
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = resolution_notes
        
        await db.commit()
        await db.refresh(alert)
        
        return alert
