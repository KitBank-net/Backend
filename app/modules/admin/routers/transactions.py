"""
Admin transaction management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.modules.transactions.models import Transaction, TransactionStatus, TransactionFee

router = APIRouter(prefix="/transactions", tags=["admin-transactions"])


@router.get("")
async def list_transactions(
    status: Optional[str] = None,
    transaction_type: Optional[str] = None,
    source_account_id: Optional[int] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all transactions with filtering"""
    query = select(Transaction)
    
    if status:
        query = query.where(Transaction.status == status)
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    if source_account_id:
        query = query.where(Transaction.source_account_id == source_account_id)
    if min_amount:
        query = query.where(Transaction.amount >= min_amount)
    if max_amount:
        query = query.where(Transaction.amount <= max_amount)
    if start_date:
        query = query.where(Transaction.created_at >= start_date)
    if end_date:
        query = query.where(Transaction.created_at <= end_date)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(Transaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return {
        "transactions": transactions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/pending-approval")
async def list_pending_approval(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List transactions pending approval"""
    query = select(Transaction).where(
        and_(
            Transaction.requires_approval == True,
            Transaction.approved_by.is_(None),
            Transaction.status != TransactionStatus.FAILED
        )
    )
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(Transaction.created_at.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return {
        "transactions": transactions,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats")
async def get_transaction_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get transaction statistics"""
    query = select(Transaction)
    if start_date:
        query = query.where(Transaction.created_at >= start_date)
    if end_date:
        query = query.where(Transaction.created_at <= end_date)
    
    # Total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    
    # Total volume
    volume_result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.status == TransactionStatus.COMPLETED
        )
    )
    
    # By status
    status_result = await db.execute(
        select(Transaction.status, func.count(Transaction.id))
        .group_by(Transaction.status)
    )
    by_status = {str(s): c for s, c in status_result.all()}
    
    # By type
    type_result = await db.execute(
        select(Transaction.transaction_type, func.count(Transaction.id))
        .group_by(Transaction.transaction_type)
    )
    by_type = {str(t): c for t, c in type_result.all()}
    
    return {
        "total_transactions": count_result.scalar() or 0,
        "total_volume": float(volume_result.scalar() or 0),
        "by_status": by_status,
        "by_type": by_type
    }


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    """Get transaction details"""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction


@router.post("/{transaction_id}/approve")
async def approve_transaction(
    transaction_id: int,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending transaction"""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction.requires_approval:
        raise HTTPException(status_code=400, detail="Transaction does not require approval")
    
    if transaction.approved_by:
        raise HTTPException(status_code=400, detail="Transaction already approved")
    
    transaction.approved_at = datetime.utcnow()
    # TODO: transaction.approved_by = current_admin.id
    transaction.status = TransactionStatus.COMPLETED
    transaction.completed_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Transaction approved", "transaction_id": transaction_id}


@router.post("/{transaction_id}/reject")
async def reject_transaction(
    transaction_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Reject a pending transaction"""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction.status = TransactionStatus.FAILED
    transaction.failed_at = datetime.utcnow()
    transaction.failure_reason = reason
    
    await db.commit()
    return {"message": "Transaction rejected", "transaction_id": transaction_id}


@router.post("/{transaction_id}/reverse")
async def reverse_transaction(
    transaction_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Reverse a completed transaction"""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.status != TransactionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Only completed transactions can be reversed")
    
    # TODO: Implement actual reversal logic (create reversal transaction, update balances)
    transaction.status = TransactionStatus.REVERSED
    transaction.internal_notes = f"Reversed: {reason}"
    
    await db.commit()
    return {"message": "Transaction reversed", "transaction_id": transaction_id}


@router.post("/{transaction_id}/refund")
async def refund_transaction(
    transaction_id: int,
    amount: Optional[Decimal] = None,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Refund a transaction (full or partial)"""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    refund_amount = amount or transaction.amount
    
    if refund_amount > transaction.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds transaction amount")
    
    # TODO: Implement actual refund logic (create refund transaction, update balances)
    return {
        "message": "Refund processed",
        "transaction_id": transaction_id,
        "refund_amount": float(refund_amount),
        "reason": reason
    }


# ============================================================
# Fee Configuration
# ============================================================

@router.get("/fees/config")
async def list_fee_configs(db: AsyncSession = Depends(get_db)):
    """List all fee configurations"""
    result = await db.execute(select(TransactionFee).order_by(TransactionFee.transaction_type))
    fees = result.scalars().all()
    return {"fees": fees}


@router.post("/fees/config")
async def create_fee_config(
    transaction_type: str,
    currency: str,
    flat_fee: Decimal = Query(Decimal("0"), ge=0),
    percentage_fee: Decimal = Query(Decimal("0"), ge=0, le=1),
    min_fee: Decimal = Query(Decimal("0"), ge=0),
    max_fee: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new fee configuration"""
    fee = TransactionFee(
        transaction_type=transaction_type,
        currency=currency,
        flat_fee=flat_fee,
        percentage_fee=percentage_fee,
        min_fee=min_fee,
        max_fee=max_fee
    )
    
    db.add(fee)
    await db.commit()
    await db.refresh(fee)
    return fee


@router.put("/fees/config/{fee_id}")
async def update_fee_config(
    fee_id: int,
    flat_fee: Optional[Decimal] = None,
    percentage_fee: Optional[Decimal] = None,
    min_fee: Optional[Decimal] = None,
    max_fee: Optional[Decimal] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update a fee configuration"""
    result = await db.execute(select(TransactionFee).where(TransactionFee.id == fee_id))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee config not found")
    
    if flat_fee is not None:
        fee.flat_fee = flat_fee
    if percentage_fee is not None:
        fee.percentage_fee = percentage_fee
    if min_fee is not None:
        fee.min_fee = min_fee
    if max_fee is not None:
        fee.max_fee = max_fee
    if is_active is not None:
        fee.is_active = is_active
    
    await db.commit()
    await db.refresh(fee)
    return fee


@router.delete("/fees/config/{fee_id}")
async def delete_fee_config(fee_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a fee configuration"""
    result = await db.execute(select(TransactionFee).where(TransactionFee.id == fee_id))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee config not found")
    
    await db.delete(fee)
    await db.commit()
    return {"message": "Fee config deleted", "id": fee_id}
