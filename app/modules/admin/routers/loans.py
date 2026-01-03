"""
Admin loan management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from app.core.database import get_db
from app.modules.loans.models import Loan, LoanProduct, LoanPayment, LoanStatus
from app.modules.users.models import User

router = APIRouter(prefix="/loans", tags=["admin-loans"])


@router.get("")
async def list_loans(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    product_id: Optional[int] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all loans with filtering"""
    query = select(Loan)
    
    if status:
        query = query.where(Loan.status == status)
    if user_id:
        query = query.where(Loan.user_id == user_id)
    if product_id:
        query = query.where(Loan.product_id == product_id)
    if min_amount:
        query = query.where(Loan.requested_amount >= min_amount)
    if max_amount:
        query = query.where(Loan.requested_amount <= max_amount)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(Loan.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    loans = result.scalars().all()
    
    return {
        "loans": loans,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/pending")
async def list_pending_loans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List loans pending approval"""
    query = select(Loan).where(Loan.status == LoanStatus.SUBMITTED)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(Loan.created_at.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    loans = result.scalars().all()
    
    return {"loans": loans, "total": total, "page": page, "page_size": page_size}


@router.get("/overdue")
async def list_overdue_loans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List overdue loans"""
    query = select(Loan).where(Loan.status == LoanStatus.OVERDUE)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    query = query.order_by(Loan.days_overdue.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    loans = result.scalars().all()
    
    return {"loans": loans, "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
async def get_loan_stats(db: AsyncSession = Depends(get_db)):
    """Get loan statistics"""
    # By status
    status_result = await db.execute(
        select(Loan.status, func.count(Loan.id), func.sum(Loan.requested_amount))
        .group_by(Loan.status)
    )
    by_status = {str(s): {"count": c, "amount": float(a or 0)} for s, c, a in status_result.all()}
    
    # Total disbursed
    disbursed = await db.execute(
        select(func.sum(Loan.disbursed_amount)).where(Loan.status.in_([
            LoanStatus.DISBURSED, LoanStatus.ACTIVE, LoanStatus.OVERDUE, LoanStatus.PAID_OFF
        ]))
    )
    
    # Total outstanding
    outstanding = await db.execute(
        select(func.sum(Loan.outstanding_balance)).where(Loan.status.in_([
            LoanStatus.ACTIVE, LoanStatus.OVERDUE
        ]))
    )
    
    return {
        "by_status": by_status,
        "total_disbursed": float(disbursed.scalar() or 0),
        "total_outstanding": float(outstanding.scalar() or 0)
    }


@router.get("/{loan_id}")
async def get_loan(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Get loan details with borrower and payment schedule"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Get borrower
    user_result = await db.execute(select(User).where(User.id == loan.user_id))
    user = user_result.scalar_one_or_none()
    
    # Get payments
    payments_result = await db.execute(
        select(LoanPayment).where(LoanPayment.loan_id == loan_id)
        .order_by(LoanPayment.payment_number)
    )
    payments = payments_result.scalars().all()
    
    # Get product
    product_result = await db.execute(
        select(LoanProduct).where(LoanProduct.id == loan.product_id)
    )
    product = product_result.scalar_one_or_none()
    
    return {
        "loan": loan,
        "borrower": user,
        "product": product,
        "payments": payments
    }


@router.post("/{loan_id}/review")
async def start_loan_review(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Mark loan as under review"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status != LoanStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Loan is not in submitted status")
    
    loan.status = LoanStatus.UNDER_REVIEW
    loan.reviewed_at = datetime.utcnow()
    await db.commit()
    return {"message": "Loan review started", "loan_id": loan_id}


@router.post("/{loan_id}/approve")
async def approve_loan(
    loan_id: int,
    approved_amount: Decimal,
    interest_rate: Decimal,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Approve a loan application"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status not in [LoanStatus.SUBMITTED, LoanStatus.UNDER_REVIEW]:
        raise HTTPException(status_code=400, detail="Loan is not pending approval")
    
    loan.status = LoanStatus.APPROVED
    loan.approved_amount = approved_amount
    loan.interest_rate = interest_rate
    loan.approval_notes = notes
    loan.approved_at = datetime.utcnow()
    # TODO: loan.reviewed_by = current_admin.id
    
    await db.commit()
    return {"message": "Loan approved", "loan_id": loan_id}


@router.post("/{loan_id}/reject")
async def reject_loan(
    loan_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Reject a loan application"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan.status = LoanStatus.REJECTED
    loan.rejection_reason = reason
    loan.rejected_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Loan rejected", "loan_id": loan_id}


@router.post("/{loan_id}/disburse")
async def disburse_loan(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Disburse an approved loan"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status != LoanStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Loan must be approved before disbursement")
    
    # TODO: Call loan service to disburse and create payment schedule
    loan.status = LoanStatus.DISBURSED
    loan.disbursed_amount = loan.approved_amount
    loan.disbursed_at = datetime.utcnow()
    loan.outstanding_balance = loan.approved_amount
    
    await db.commit()
    return {"message": "Loan disbursed", "loan_id": loan_id}


@router.post("/{loan_id}/mark-active")
async def mark_loan_active(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a disbursed loan as active"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan.status = LoanStatus.ACTIVE
    await db.commit()
    return {"message": "Loan marked as active", "loan_id": loan_id}


@router.post("/{loan_id}/mark-overdue")
async def mark_loan_overdue(
    loan_id: int,
    days_overdue: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db)
):
    """Mark a loan as overdue"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan.status = LoanStatus.OVERDUE
    loan.days_overdue = days_overdue
    await db.commit()
    return {"message": "Loan marked as overdue", "loan_id": loan_id}


@router.post("/{loan_id}/write-off")
async def write_off_loan(
    loan_id: int,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Write off a loan"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan.status = LoanStatus.WRITTEN_OFF
    await db.commit()
    return {"message": "Loan written off", "loan_id": loan_id, "reason": reason}


@router.post("/{loan_id}/mark-paid")
async def mark_loan_paid(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a loan as fully paid"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan.status = LoanStatus.PAID_OFF
    loan.outstanding_balance = Decimal("0")
    loan.paid_off_at = datetime.utcnow()
    await db.commit()
    return {"message": "Loan marked as paid", "loan_id": loan_id}


# ============================================================
# Loan Products CRUD
# ============================================================

@router.get("/products/all")
async def list_loan_products(db: AsyncSession = Depends(get_db)):
    """List all loan products"""
    result = await db.execute(select(LoanProduct).order_by(LoanProduct.name))
    products = result.scalars().all()
    return {"products": products}


@router.post("/products")
async def create_loan_product(
    name: str,
    loan_type: str,
    min_amount: Decimal,
    max_amount: Decimal,
    min_interest_rate: Decimal,
    max_interest_rate: Decimal,
    default_interest_rate: Decimal,
    min_term_months: int,
    max_term_months: int,
    description: Optional[str] = None,
    processing_fee_percentage: Decimal = Decimal("0"),
    late_payment_fee: Decimal = Decimal("0"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new loan product"""
    product = LoanProduct(
        name=name,
        loan_type=loan_type,
        description=description,
        min_amount=min_amount,
        max_amount=max_amount,
        min_interest_rate=min_interest_rate,
        max_interest_rate=max_interest_rate,
        default_interest_rate=default_interest_rate,
        min_term_months=min_term_months,
        max_term_months=max_term_months,
        processing_fee_percentage=processing_fee_percentage,
        late_payment_fee=late_payment_fee
    )
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/products/{product_id}")
async def get_loan_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Get loan product details"""
    result = await db.execute(select(LoanProduct).where(LoanProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}")
async def update_loan_product(
    product_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    default_interest_rate: Optional[Decimal] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update a loan product"""
    result = await db.execute(select(LoanProduct).where(LoanProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if name is not None:
        product.name = name
    if description is not None:
        product.description = description
    if min_amount is not None:
        product.min_amount = min_amount
    if max_amount is not None:
        product.max_amount = max_amount
    if default_interest_rate is not None:
        product.default_interest_rate = default_interest_rate
    if is_active is not None:
        product.is_active = is_active
    
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}")
async def delete_loan_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a loan product (soft delete by deactivating)"""
    result = await db.execute(select(LoanProduct).where(LoanProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product has loans
    loans_result = await db.execute(
        select(func.count(Loan.id)).where(Loan.product_id == product_id)
    )
    loan_count = loans_result.scalar()
    
    if loan_count > 0:
        # Soft delete
        product.is_active = False
        await db.commit()
        return {"message": "Product deactivated (has existing loans)", "id": product_id}
    else:
        # Hard delete
        await db.delete(product)
        await db.commit()
        return {"message": "Product deleted", "id": product_id}
