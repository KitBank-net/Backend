"""
Admin system settings and audit log endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.modules.admin.models import SystemSetting, AuditLog
from app.modules.admin.schemas import AuditLogListResponse, AuditLogResponse, AuditLogFilter
from app.modules.admin.services import AdminService

router = APIRouter(tags=["admin-settings"])


# ============================================================
# System Settings
# ============================================================

@router.get("/settings")
async def list_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List system settings"""
    query = select(SystemSetting)
    if category:
        query = query.where(SystemSetting.category == category)
    query = query.order_by(SystemSetting.category, SystemSetting.key)
    
    result = await db.execute(query)
    settings = result.scalars().all()
    return {"settings": settings}


@router.get("/settings/categories")
async def list_setting_categories(db: AsyncSession = Depends(get_db)):
    """List all setting categories"""
    result = await db.execute(
        select(SystemSetting.category).distinct().order_by(SystemSetting.category)
    )
    categories = [c[0] for c in result.all()]
    return {"categories": categories}


@router.get("/settings/{key}")
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Get a specific setting"""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    value: str,
    db: AsyncSession = Depends(get_db)
):
    """Update a system setting"""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    if setting.is_readonly:
        raise HTTPException(status_code=400, detail="Setting is read-only")
    
    old_value = setting.value
    setting.value = value
    setting.updated_at = datetime.utcnow()
    # TODO: setting.updated_by = current_admin.id
    
    await db.commit()
    return {
        "message": "Setting updated",
        "key": key,
        "old_value": old_value,
        "new_value": value
    }


@router.post("/settings")
async def create_setting(
    key: str,
    value: str,
    category: str,
    value_type: str = "string",
    description: Optional[str] = None,
    is_sensitive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Create a new system setting"""
    # Check if exists
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Setting already exists")
    
    setting = SystemSetting(
        key=key,
        value=value,
        value_type=value_type,
        category=category,
        description=description,
        is_sensitive=is_sensitive
    )
    
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return setting


@router.delete("/settings/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Delete a system setting"""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    if setting.is_readonly:
        raise HTTPException(status_code=400, detail="Cannot delete read-only setting")
    
    await db.delete(setting)
    await db.commit()
    return {"message": "Setting deleted", "key": key}


# ============================================================
# Audit Logs
# ============================================================

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    admin_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    success: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with filtering"""
    service = AdminService(db)
    
    filters = AuditLogFilter(
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        success=success,
        start_date=start_date,
        end_date=end_date
    )
    
    logs, total = await service.get_audit_logs(filters, page, page_size)
    total_pages = (total + page_size - 1) // page_size
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/audit-logs/actions")
async def list_audit_actions(db: AsyncSession = Depends(get_db)):
    """List all distinct audit log actions"""
    result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    actions = [a[0] for a in result.all()]
    return {"actions": actions}


@router.get("/audit-logs/resource-types")
async def list_audit_resource_types(db: AsyncSession = Depends(get_db)):
    """List all distinct audit log resource types"""
    result = await db.execute(
        select(AuditLog.resource_type).distinct().order_by(AuditLog.resource_type)
    )
    types = [t[0] for t in result.all()]
    return {"resource_types": types}


@router.get("/audit-logs/{log_id}")
async def get_audit_log(log_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific audit log entry"""
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
