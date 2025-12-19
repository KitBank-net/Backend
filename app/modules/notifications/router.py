from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.notifications import schemas
from app.modules.notifications.services import NotificationService
from app.modules.notifications.models import NotificationType, NotificationStatus

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=schemas.NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    unread_only: bool = Query(False, description="Only show unread"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get paginated list of notifications for the current user.
    
    - Supports filtering by type and read status
    - Returns total count and unread count
    """
    skip = (page - 1) * limit
    
    type_filter = None
    if notification_type:
        try:
            type_filter = NotificationType(notification_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notification type: {notification_type}"
            )

    notifications, total, unread_count = await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        notification_type=type_filter,
        unread_only=unread_only
    )

    return schemas.NotificationListResponse(
        notifications=[schemas.NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        limit=limit
    )


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get count of unread notifications"""
    _, _, unread_count = await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        skip=0,
        limit=1
    )
    return {"unread_count": unread_count}


@router.get("/preferences", response_model=schemas.NotificationPreferenceResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get notification preferences for current user.
    
    - Creates default preferences if not exists
    """
    preferences = await NotificationService.get_or_create_preferences(db, current_user.id)
    return preferences


@router.put("/preferences", response_model=schemas.NotificationPreferenceResponse)
async def update_preferences(
    preference_update: schemas.NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update notification preferences.
    
    - Control which channels are enabled (SMS, Email, Push)
    - Control which notification types to receive
    - Set quiet hours and thresholds
    """
    preferences = await NotificationService.update_preferences(
        db=db,
        user_id=current_user.id,
        preference_update=preference_update
    )
    return preferences


@router.get("/{notification_id}", response_model=schemas.NotificationResponse)
async def get_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific notification by ID"""
    notification = await NotificationService.get_notification(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.put("/{notification_id}/read", response_model=schemas.NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a specific notification as read"""
    notification = await NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.put("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark all notifications as read"""
    count = await NotificationService.mark_all_as_read(db, current_user.id)
    return {"message": f"Marked {count} notifications as read", "count": count}


@router.delete("/{notification_id}", status_code=status.HTTP_200_OK)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a notification"""
    success = await NotificationService.delete_notification(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return {"message": "Notification deleted successfully"}
