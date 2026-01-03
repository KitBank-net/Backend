"""
Admin authentication endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.modules.admin.schemas import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse,
    AdminLoginRequest, AdminLoginResponse
)
from app.modules.admin.services import AdminService
from app.modules.admin.models import AdminUser

router = APIRouter(tags=["admin-auth"])


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Admin login"""
    service = AdminService(db)
    
    try:
        admin = await service.authenticate_admin(request.email, request.password)
        
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if admin.two_factor_enabled and not request.otp_code:
            raise HTTPException(status_code=401, detail="OTP required")
        
        token = create_access_token(
            data={"sub": admin.email, "type": "admin", "admin_id": admin.id}
        )
        
        await service.log_action(
            admin_id=admin.id,
            admin_email=admin.email,
            action="login",
            resource_type="admin",
            resource_id=admin.id,
            description="Admin login successful"
        )
        
        permissions = service.get_admin_permissions(admin)
        
        return AdminLoginResponse(
            access_token=token,
            admin=AdminUserResponse.model_validate(admin),
            permissions=permissions
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/admins", response_model=AdminUserResponse)
async def create_admin_user(
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new admin user"""
    service = AdminService(db)
    try:
        admin = await service.create_admin_user(data)
        return admin
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admins", response_model=list[AdminUserResponse])
async def list_admin_users(db: AsyncSession = Depends(get_db)):
    """List all admin users"""
    service = AdminService(db)
    return await service.get_all_admins()


@router.get("/admins/{admin_id}", response_model=AdminUserResponse)
async def get_admin_user(admin_id: int, db: AsyncSession = Depends(get_db)):
    """Get admin user details"""
    service = AdminService(db)
    admin = await service.get_admin_user(admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin


@router.put("/admins/{admin_id}", response_model=AdminUserResponse)
async def update_admin_user(
    admin_id: int,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update admin user"""
    from sqlalchemy import select
    
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(admin, field, value)
    
    await db.commit()
    await db.refresh(admin)
    return admin


@router.delete("/admins/{admin_id}")
async def delete_admin_user(admin_id: int, db: AsyncSession = Depends(get_db)):
    """Delete admin user"""
    from sqlalchemy import select
    
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    await db.delete(admin)
    await db.commit()
    return {"message": "Admin deleted", "id": admin_id}






