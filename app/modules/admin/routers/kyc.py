"""
Admin KYC management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.modules.users.models import User, KYCStatus

router = APIRouter(prefix="/kyc", tags=["admin-kyc"])


@router.get("/pending")
async def list_pending_kyc(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List users with pending KYC"""
    query = select(User).where(User.kyc_status == KYCStatus.SUBMITTED)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(User.created_at.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats")
async def get_kyc_stats(db: AsyncSession = Depends(get_db)):
    """Get KYC statistics"""
    statuses = [KYCStatus.PENDING, KYCStatus.SUBMITTED, KYCStatus.UNDER_REVIEW, 
                KYCStatus.APPROVED, KYCStatus.REJECTED]
    
    stats = {}
    for status in statuses:
        result = await db.execute(
            select(func.count(User.id)).where(User.kyc_status == status)
        )
        stats[status.value] = result.scalar() or 0
    
    return stats


@router.get("/{user_id}")
async def get_kyc_details(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get KYC details for a user"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": f"{user.first_name} {user.last_name}",
        "phone_number": user.phone_number,
        "date_of_birth": user.date_of_birth,
        "nationality": user.nationality,
        "country_of_residence": user.country_of_residence,
        "address": {
            "street": user.street_address,
            "city": user.city,
            "state": user.state,
            "postal_code": user.postal_code,
            "country": user.country
        },
        "occupation": user.occupation,
        "source_of_funds": user.source_of_funds,
        "monthly_income_range": user.monthly_income_range,
        "tax_identification_number": user.tax_identification_number,
        "kyc_status": user.kyc_status,
        "kyc_rejection_reason": user.kyc_rejection_reason,
        "kyc_verified_at": user.kyc_verified_at,
        "kyc_reviewer_id": user.kyc_reviewer_id,
        "created_at": user.created_at
    }


@router.post("/{user_id}/start-review")
async def start_kyc_review(user_id: int, db: AsyncSession = Depends(get_db)):
    """Mark KYC as under review"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status != KYCStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="KYC is not in submitted status")
    
    user.kyc_status = KYCStatus.UNDER_REVIEW
    await db.commit()
    return {"message": "KYC review started", "user_id": user_id}


@router.post("/{user_id}/approve")
async def approve_kyc(
    user_id: int,
    notes: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Approve user KYC"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status not in [KYCStatus.SUBMITTED, KYCStatus.UNDER_REVIEW]:
        raise HTTPException(status_code=400, detail="KYC is not pending review")
    
    user.kyc_status = KYCStatus.APPROVED
    user.kyc_verified_at = datetime.utcnow()
    # TODO: user.kyc_reviewer_id = current_admin.id
    
    await db.commit()
    return {"message": "KYC approved", "user_id": user_id}


@router.post("/{user_id}/reject")
async def reject_kyc(
    user_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Reject user KYC"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status not in [KYCStatus.SUBMITTED, KYCStatus.UNDER_REVIEW]:
        raise HTTPException(status_code=400, detail="KYC is not pending review")
    
    user.kyc_status = KYCStatus.REJECTED
    user.kyc_rejection_reason = reason
    
    await db.commit()
    return {"message": "KYC rejected", "user_id": user_id, "reason": reason}


@router.post("/{user_id}/request-resubmission")
async def request_kyc_resubmission(
    user_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Request KYC resubmission"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.kyc_status = KYCStatus.PENDING
    user.kyc_rejection_reason = f"Resubmission required: {reason}"
    
    await db.commit()
    return {"message": "Resubmission requested", "user_id": user_id}
