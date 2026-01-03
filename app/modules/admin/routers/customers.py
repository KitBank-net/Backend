"""
Admin customer management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from passlib.context import CryptContext

from app.core.database import get_db
from app.modules.users.models import User, AccountStatus
from app.modules.accounts.models import Account
from app.modules.loans.models import Loan
from app.modules.cards.models import VirtualCard
from app.modules.transactions.models import Transaction

router = APIRouter(prefix="/customers", tags=["admin-customers"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("")
async def list_customers(
    search: Optional[str] = None,
    kyc_status: Optional[str] = None,
    account_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all customers with filtering"""
    query = select(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_term),
                User.phone_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
    
    if kyc_status:
        query = query.where(User.kyc_status == kyc_status)
    if account_status:
        query = query.where(User.account_status == account_status)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/{user_id}")
async def get_customer(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get customer details with all related data"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get accounts
    accounts_result = await db.execute(
        select(Account).where(Account.user_id == user_id)
    )
    accounts = accounts_result.scalars().all()
    
    # Get loans
    loans_result = await db.execute(
        select(Loan).where(Loan.user_id == user_id)
    )
    loans = loans_result.scalars().all()
    
    # Get cards
    cards_result = await db.execute(
        select(VirtualCard).where(VirtualCard.user_id == user_id)
    )
    cards = cards_result.scalars().all()
    
    # Recent transactions
    if accounts:
        account_ids = [a.id for a in accounts]
        txn_result = await db.execute(
            select(Transaction).where(
                or_(
                    Transaction.source_account_id.in_(account_ids),
                    Transaction.destination_account_id.in_(account_ids)
                )
            ).order_by(Transaction.created_at.desc()).limit(10)
        )
        transactions = txn_result.scalars().all()
    else:
        transactions = []
    
    return {
        "user": user,
        "accounts": accounts,
        "loans": loans,
        "cards": cards,
        "recent_transactions": transactions
    }


@router.put("/{user_id}")
async def update_customer(
    user_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update customer details"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    if phone_number:
        user.phone_number = phone_number
    
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/verify-email")
async def verify_customer_email(user_id: int, db: AsyncSession = Depends(get_db)):
    """Manually verify customer email"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.email_verified = True
    await db.commit()
    return {"message": "Email verified", "user_id": user_id}


@router.post("/{user_id}/verify-phone")
async def verify_customer_phone(user_id: int, db: AsyncSession = Depends(get_db)):
    """Manually verify customer phone"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.phone_verified = True
    await db.commit()
    return {"message": "Phone verified", "user_id": user_id}


@router.post("/{user_id}/suspend")
async def suspend_customer(
    user_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Suspend a customer account"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.account_status = AccountStatus.SUSPENDED
    await db.commit()
    return {"message": "User suspended", "user_id": user_id}


@router.post("/{user_id}/reactivate")
async def reactivate_customer(user_id: int, db: AsyncSession = Depends(get_db)):
    """Reactivate a suspended customer"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.account_status = AccountStatus.ACTIVE
    await db.commit()
    return {"message": "User reactivated", "user_id": user_id}


@router.post("/{user_id}/unlock")
async def unlock_customer(user_id: int, db: AsyncSession = Depends(get_db)):
    """Unlock a locked customer account"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.login_attempts = 0
    user.account_locked_until = None
    await db.commit()
    return {"message": "User unlocked", "user_id": user_id}


@router.post("/{user_id}/reset-password")
async def reset_customer_password(
    user_id: int,
    new_password: str = Query(..., min_length=8),
    db: AsyncSession = Depends(get_db)
):
    """Reset customer password"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = pwd_context.hash(new_password)
    user.login_attempts = 0
    user.account_locked_until = None
    await db.commit()
    return {"message": "Password reset", "user_id": user_id}


@router.delete("/{user_id}")
async def delete_customer(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a customer account"""
    from datetime import datetime
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.account_status = AccountStatus.CLOSED
    user.deleted_at = datetime.utcnow()
    await db.commit()
    return {"message": "User deleted (soft)", "user_id": user_id}
