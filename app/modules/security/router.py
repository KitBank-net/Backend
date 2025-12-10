from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.security import schemas, services

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.get("/login-history", response_model=List[schemas.LoginHistoryResponse])
async def get_login_history(
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user login history.
    
    - Shows last 50 login attempts by default
    - Includes successful and failed attempts
    """
    history = await services.SecurityService.get_login_history(db, current_user.id, limit)
    return history


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout from all devices.
    
    - Invalidates all active sessions
    - Requires re-login on all devices
    """
    # TODO: Implement session invalidation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Logout all not yet implemented"
    )


@router.get("/devices", response_model=List[schemas.TrustedDeviceResponse])
async def list_trusted_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List trusted devices.
    """
    devices = await services.SecurityService.get_trusted_devices(db, current_user.id)
    return devices


@router.delete("/devices/{device_id}", status_code=status.HTTP_200_OK)
async def remove_trusted_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove trusted device.
    
    - Device will require 2FA on next login
    """
    await services.SecurityService.remove_trusted_device(db, device_id, current_user.id)
    return {"message": "Device removed successfully"}


@router.post("/devices/{device_id}/trust", status_code=status.HTTP_200_OK)
async def trust_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark device as trusted.
    """
    # TODO: Implement device trust management
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Device trust not yet implemented"
    )


@router.get("/alerts", response_model=List[schemas.SecurityAlertResponse])
async def get_security_alerts(
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get security alerts.
    """
    alerts = await services.SecurityService.get_security_alerts(db, current_user.id, limit)
    return alerts


@router.put("/alerts/{alert_id}/resolve", response_model=schemas.SecurityAlertResponse)
async def resolve_alert(
    alert_id: int,
    resolve_data: schemas.ResolveAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Resolve security alert.
    """
    alert = await services.SecurityService.resolve_alert(
        db, alert_id, current_user.id, resolve_data.resolution_notes
    )
    return alert


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Change password with old password verification.
    """
    # TODO: Implement password change (already in users module)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use /api/v1/users/profile for password changes"
    )


@router.post("/session/refresh", status_code=status.HTTP_200_OK)
async def refresh_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Refresh session token.
    """
    # TODO: Implement token refresh
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented"
    )


@router.get("/session/active", status_code=status.HTTP_200_OK)
async def get_active_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get active sessions.
    """
    # TODO: Implement session listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session listing not yet implemented"
    )


@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def terminate_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Terminate specific session.
    """
    # TODO: Implement session termination
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session termination not yet implemented"
    )


@router.post("/report/suspicious", status_code=status.HTTP_201_CREATED)
async def report_suspicious_activity(
    report_data: schemas.ReportSuspiciousRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Report suspicious activity.
    """
    from app.modules.security.models import AlertType, Severity
    
    # Create security alert
    alert = await services.SecurityService.create_security_alert(
        db,
        current_user.id,
        AlertType.SUSPICIOUS_LOGIN,  # Would categorize based on incident_type
        Severity.HIGH,
        report_data.description
    )
    
    return {"message": "Report submitted successfully", "alert_id": alert.id}


@router.get("/compliance/aml-status", status_code=status.HTTP_200_OK)
async def get_aml_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AML check status.
    """
    # TODO: Implement AML status retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AML status not yet implemented"
    )


@router.post("/verify-identity", status_code=status.HTTP_200_OK)
async def submit_additional_verification(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit additional identity verification.
    """
    # TODO: Implement additional verification
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Additional verification not yet implemented"
    )


@router.get("/audit-logs", status_code=status.HTTP_200_OK)
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get security audit logs (admin).
    """
    # TODO: Implement audit log retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Audit logs not yet implemented"
    )
