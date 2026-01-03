"""
Admin account management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from decimal import Decimal

from app.core.database import get_db
from app.modules.accounts.models import Account, AccountStatusEnum
from app.modules.users.models import User
from app.modules.transactions.models import Transaction

router = APIRouter(prefix="/accounts", tags=["admin-accounts"])


@router.get("")
async def list_accounts(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    account_type: Optional[str] = None,
    min_balance: Optional[Decimal] = None,
    max_balance: Optional[Decimal] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all accounts with filtering"""
    query = select(Account)
    
    if status:
        query = query.where(Account.account_status == status)
    if user_id:
        query = query.where(Account.user_id == user_id)
    if account_type:
        query = query.where(Account.account_type == account_type)
    if min_balance is not None:
        query = query.where(Account.current_balance >= min_balance)
    if max_balance is not None:
        query = query.where(Account.current_balance <= max_balance)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(Account.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return {
        "accounts": accounts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/stats")
async def get_account_stats(db: AsyncSession = Depends(get_db)):
    """Get account statistics"""
    # Total accounts
    total = await db.execute(select(func.count(Account.id)))
    
    # By status
    statuses = [AccountStatusEnum.ACTIVE, AccountStatusEnum.INACTIVE, 
                AccountStatusEnum.FROZEN, AccountStatusEnum.CLOSED]
    by_status = {}
    for status in statuses:
        result = await db.execute(
            select(func.count(Account.id)).where(Account.account_status == status)
        )
        by_status[status.value] = result.scalar() or 0
    
    # Total balances
    balance_result = await db.execute(select(func.sum(Account.current_balance)))
    
    return {
        "total_accounts": total.scalar() or 0,
        "by_status": by_status,
        "total_balance": float(balance_result.scalar() or 0)
    }


@router.get("/{account_id}")
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Get account details with owner and recent transactions"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get owner
    user_result = await db.execute(select(User).where(User.id == account.user_id))
    user = user_result.scalar_one_or_none()
    
    # Get recent transactions
    txn_result = await db.execute(
        select(Transaction).where(
            or_(
                Transaction.source_account_id == account_id,
                Transaction.destination_account_id == account_id
            )
        ).order_by(Transaction.created_at.desc()).limit(20)
    )
    transactions = txn_result.scalars().all()
    
    return {
        "account": account,
        "owner": user,
        "recent_transactions": transactions
    }


@router.post("/{account_id}/freeze")
async def freeze_account(
    account_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Freeze an account"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.account_status = AccountStatusEnum.FROZEN
    await db.commit()
    return {"message": "Account frozen", "account_id": account_id, "reason": reason}


@router.post("/{account_id}/unfreeze")
async def unfreeze_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Unfreeze an account"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.account_status = AccountStatusEnum.ACTIVE
    await db.commit()
    return {"message": "Account unfrozen", "account_id": account_id}


@router.post("/{account_id}/close")
async def close_account(
    account_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Close an account"""
    from datetime import date
    
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.current_balance != 0:
        raise HTTPException(status_code=400, detail="Account must have zero balance to close")
    
    account.account_status = AccountStatusEnum.CLOSED
    account.closed_date = date.today()
    account.closure_reason = reason
    await db.commit()
    return {"message": "Account closed", "account_id": account_id}


@router.post("/{account_id}/adjust-balance")
async def adjust_account_balance(
    account_id: int,
    amount: Decimal = Query(..., description="Positive to credit, negative to debit"),
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Manually adjust account balance"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    old_balance = account.current_balance
    account.current_balance += amount
    account.available_balance += amount
    account.ledger_balance += amount
    
    await db.commit()
    
    return {
        "message": "Balance adjusted",
        "account_id": account_id,
        "old_balance": float(old_balance),
        "new_balance": float(account.current_balance),
        "adjustment": float(amount),
        "reason": reason
    }


@router.put("/{account_id}/limits")
async def update_account_limits(
    account_id: int,
    daily_transaction_limit: Optional[Decimal] = None,
    daily_withdrawal_limit: Optional[Decimal] = None,
    monthly_transaction_limit: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update account transaction limits"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if daily_transaction_limit is not None:
        account.daily_transaction_limit = daily_transaction_limit
    if daily_withdrawal_limit is not None:
        account.daily_withdrawal_limit = daily_withdrawal_limit
    if monthly_transaction_limit is not None:
        account.monthly_transaction_limit = monthly_transaction_limit
    
    await db.commit()
    await db.refresh(account)
    return {"message": "Limits updated", "account": account}


@router.put("/{account_id}/features")
async def update_account_features(
    account_id: int,
    wire_transfer_enabled: Optional[bool] = None,
    international_transfer_enabled: Optional[bool] = None,
    bill_pay_enabled: Optional[bool] = None,
    overdraft_enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update account feature flags"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if wire_transfer_enabled is not None:
        account.wire_transfer_enabled = wire_transfer_enabled
    if international_transfer_enabled is not None:
        account.international_transfer_enabled = international_transfer_enabled
    if bill_pay_enabled is not None:
        account.bill_pay_enabled = bill_pay_enabled
    if overdraft_enabled is not None:
        account.overdraft_enabled = overdraft_enabled
    
    await db.commit()
    await db.refresh(account)
    return {"message": "Features updated", "account": account}
