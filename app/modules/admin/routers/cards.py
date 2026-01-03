"""
Admin card management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.modules.cards.models import VirtualCard, CardStatus

router = APIRouter(prefix="/cards", tags=["admin-cards"])


@router.get("")
async def list_cards(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    card_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all virtual cards with filtering"""
    query = select(VirtualCard)
    
    if status:
        query = query.where(VirtualCard.status == status)
    if user_id:
        query = query.where(VirtualCard.user_id == user_id)
    if card_type:
        query = query.where(VirtualCard.card_type == card_type)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(VirtualCard.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    cards = result.scalars().all()
    
    return {
        "cards": cards,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/stats")
async def get_card_stats(db: AsyncSession = Depends(get_db)):
    """Get card statistics"""
    # Total cards
    total = await db.execute(select(func.count(VirtualCard.id)))
    
    # By status
    statuses = [CardStatus.ACTIVE, CardStatus.BLOCKED, CardStatus.EXPIRED, CardStatus.CANCELLED]
    by_status = {}
    for status in statuses:
        result = await db.execute(
            select(func.count(VirtualCard.id)).where(VirtualCard.status == status)
        )
        by_status[status.value] = result.scalar() or 0
    
    # Total balance
    balance_result = await db.execute(select(func.sum(VirtualCard.balance)))
    
    return {
        "total_cards": total.scalar() or 0,
        "by_status": by_status,
        "total_balance": float(balance_result.scalar() or 0)
    }


@router.get("/{card_id}")
async def get_card(card_id: int, db: AsyncSession = Depends(get_db)):
    """Get card details"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.post("/{card_id}/activate")
async def activate_card(card_id: int, db: AsyncSession = Depends(get_db)):
    """Activate a card"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card.status == CardStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot activate a cancelled card")
    
    card.status = CardStatus.ACTIVE
    await db.commit()
    return {"message": "Card activated", "card_id": card_id}


@router.post("/{card_id}/block")
async def block_card(
    card_id: int,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db)
):
    """Block a card"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    card.status = CardStatus.BLOCKED
    card.blocked_reason = reason
    card.blocked_at = datetime.utcnow()
    await db.commit()
    return {"message": "Card blocked", "card_id": card_id, "reason": reason}


@router.post("/{card_id}/unblock")
async def unblock_card(card_id: int, db: AsyncSession = Depends(get_db)):
    """Unblock a card"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    card.status = CardStatus.ACTIVE
    card.blocked_reason = None
    card.blocked_at = None
    await db.commit()
    return {"message": "Card unblocked", "card_id": card_id}


@router.post("/{card_id}/cancel")
async def cancel_card(
    card_id: int,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a card permanently"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    card.status = CardStatus.CANCELLED
    await db.commit()
    return {"message": "Card cancelled", "card_id": card_id, "reason": reason}


@router.put("/{card_id}/limits")
async def update_card_limits(
    card_id: int,
    daily_limit: Optional[Decimal] = None,
    monthly_limit: Optional[Decimal] = None,
    transaction_limit: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update card spending limits"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if daily_limit is not None:
        card.daily_limit = daily_limit
    if monthly_limit is not None:
        card.monthly_limit = monthly_limit
    if transaction_limit is not None:
        card.transaction_limit = transaction_limit
    
    await db.commit()
    await db.refresh(card)
    return {"message": "Card limits updated", "card": card}


@router.post("/{card_id}/adjust-balance")
async def adjust_card_balance(
    card_id: int,
    amount: Decimal = Query(..., description="Positive to credit, negative to debit"),
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db)
):
    """Adjust card balance manually"""
    result = await db.execute(select(VirtualCard).where(VirtualCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    old_balance = card.balance
    card.balance += amount
    
    await db.commit()
    
    return {
        "message": "Card balance adjusted",
        "card_id": card_id,
        "old_balance": float(old_balance),
        "new_balance": float(card.balance),
        "adjustment": float(amount),
        "reason": reason
    }
