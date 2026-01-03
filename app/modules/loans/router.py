from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.loans.schemas import (
    # Product schemas
    LoanProductResponse, LoanProductCreate,
    # Application schemas
    LoanApplicationRequest, LoanApprovalRequest, LoanRejectionRequest,
    LoanDisbursementRequest,
    # Response schemas
    LoanResponse, LoanListResponse, LoanDetailResponse,
    # Repayment schemas
    LoanRepaymentRequest, LoanEarlyPayoffRequest, LoanRepaymentResponse,
    # Eligibility & Calculator
    LoanEligibilityRequest, LoanEligibilityResponse,
    LoanCalculatorRequest, LoanCalculatorResponse,
    # Summary
    LoanSummary, LoanStatus
)
from app.modules.loans.services import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])


# ============================================================
# Loan Products
# ============================================================

@router.get("/products", response_model=List[LoanProductResponse])
async def get_loan_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all available loan products"""
    service = LoanService(db)
    products = await service.get_loan_products()
    return products


@router.get("/products/{product_id}", response_model=LoanProductResponse)
async def get_loan_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific loan product details"""
    service = LoanService(db)
    product = await service.get_loan_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Loan product not found")
    return product


# ============================================================
# Loan Calculator & Eligibility
# ============================================================

@router.post("/calculator", response_model=LoanCalculatorResponse)
async def calculate_loan(
    request: LoanCalculatorRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Calculate loan details and amortization schedule"""
    # Calculator doesn't need DB
    from app.modules.loans.services import LoanService
    service = LoanService(None)  # No DB needed for calculation
    return service.calculate_loan(request)


@router.post("/eligibility", response_model=LoanEligibilityResponse)
async def check_eligibility(
    request: LoanEligibilityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check loan eligibility before applying"""
    service = LoanService(db)
    return await service.check_eligibility(current_user.id, request)


# ============================================================
# Loan Application
# ============================================================

@router.post("/apply", response_model=LoanResponse)
async def apply_for_loan(
    request: LoanApplicationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Apply for a new loan"""
    service = LoanService(db)
    try:
        loan = await service.apply_for_loan(current_user.id, request)
        return loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loan_id}/submit", response_model=LoanResponse)
async def submit_loan_application(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit a draft loan application for review"""
    service = LoanService(db)
    try:
        loan = await service.submit_loan_application(loan_id, current_user.id)
        return loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loan_id}/cancel", response_model=LoanResponse)
async def cancel_loan_application(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a loan application (only if draft or submitted)"""
    service = LoanService(db)
    loan = await service.get_user_loan(loan_id, current_user.id)
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status not in [LoanStatus.DRAFT, LoanStatus.SUBMITTED]:
        raise HTTPException(status_code=400, detail="Cannot cancel loan at this stage")
    
    loan.status = LoanStatus.CANCELLED
    await db.commit()
    await db.refresh(loan)
    
    return loan


# ============================================================
# Loan Queries
# ============================================================

@router.get("/", response_model=LoanListResponse)
async def get_my_loans(
    status: Optional[LoanStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all my loans"""
    service = LoanService(db)
    loans, total = await service.get_user_loans(
        current_user.id, status, page, page_size
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return LoanListResponse(
        loans=loans,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/summary", response_model=LoanSummary)
async def get_loan_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get loan summary for dashboard"""
    service = LoanService(db)
    return await service.get_loan_summary(current_user.id)


@router.get("/{loan_id}", response_model=LoanDetailResponse)
async def get_loan_details(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed loan information including payment schedule"""
    service = LoanService(db)
    result = await service.get_loan_with_schedule(loan_id, current_user.id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan = result["loan"]
    schedule = result["payment_schedule"]
    
    # Build response with schedule
    response = LoanDetailResponse(
        id=loan.id,
        reference_number=loan.reference_number,
        user_id=loan.user_id,
        account_id=loan.account_id,
        product_id=loan.product_id,
        loan_type=loan.loan_type,
        purpose=loan.purpose,
        requested_amount=loan.requested_amount,
        approved_amount=loan.approved_amount,
        disbursed_amount=loan.disbursed_amount,
        currency=loan.currency,
        interest_rate=loan.interest_rate,
        term_months=loan.term_months,
        repayment_frequency=loan.repayment_frequency,
        total_interest=loan.total_interest,
        total_repayment=loan.total_repayment,
        monthly_payment=loan.monthly_payment,
        principal_paid=loan.principal_paid,
        interest_paid=loan.interest_paid,
        total_paid=loan.total_paid,
        outstanding_balance=loan.outstanding_balance,
        processing_fee=loan.processing_fee,
        late_fees_accrued=loan.late_fees_accrued,
        status=loan.status,
        application_date=loan.application_date,
        approved_at=loan.approved_at,
        disbursed_at=loan.disbursed_at,
        first_payment_date=loan.first_payment_date,
        maturity_date=loan.maturity_date,
        next_payment_date=loan.next_payment_date,
        payments_made=loan.payments_made,
        payments_remaining=loan.payments_remaining,
        days_overdue=loan.days_overdue,
        collateral_type=loan.collateral_type,
        collateral_description=loan.collateral_description,
        collateral_value=loan.collateral_value,
        employer_name=loan.employer_name,
        monthly_income=loan.monthly_income,
        rejection_reason=loan.rejection_reason,
        approval_notes=loan.approval_notes,
        payment_schedule=schedule
    )
    
    return response


# ============================================================
# Loan Repayment
# ============================================================

@router.post("/{loan_id}/pay", response_model=LoanRepaymentResponse)
async def make_loan_payment(
    loan_id: int,
    request: LoanRepaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Make a loan payment"""
    if request.loan_id != loan_id:
        raise HTTPException(status_code=400, detail="Loan ID mismatch")
    
    service = LoanService(db)
    try:
        result = await service.make_payment(request, current_user.id)
        return LoanRepaymentResponse(
            payment_id=result["payment_id"],
            loan_id=result["loan_id"],
            amount_paid=result["amount_paid"],
            principal_paid=result.get("principal_paid", result["amount_paid"]),
            interest_paid=result.get("interest_paid", 0),
            late_fee_paid=result.get("late_fee_paid", 0),
            new_balance=result["new_balance"],
            payment_date=datetime.utcnow(),
            loan_status=result["loan_status"],
            payments_remaining=result["payments_remaining"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loan_id}/payoff", response_model=LoanResponse)
async def payoff_loan(
    loan_id: int,
    request: LoanEarlyPayoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pay off entire loan early"""
    if request.loan_id != loan_id:
        raise HTTPException(status_code=400, detail="Loan ID mismatch")
    
    service = LoanService(db)
    try:
        loan = await service.payoff_loan(request, current_user.id)
        return loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{loan_id}/payoff-amount")
async def get_payoff_amount(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the amount needed to pay off the loan"""
    service = LoanService(db)
    loan = await service.get_user_loan(loan_id, current_user.id)
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
        raise HTTPException(status_code=400, detail="Loan is not active")
    
    payoff_amount = loan.outstanding_balance + loan.late_fees_accrued
    
    return {
        "loan_id": loan.id,
        "outstanding_balance": loan.outstanding_balance,
        "late_fees": loan.late_fees_accrued,
        "total_payoff_amount": payoff_amount,
        "currency": loan.currency
    }


# ============================================================
# Admin Endpoints (would typically have admin role check)
# ============================================================

@router.post("/admin/approve", response_model=LoanResponse)
async def approve_loan(
    request: LoanApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Approve a loan application (Admin)"""
    # TODO: Add admin role check
    service = LoanService(db)
    try:
        loan = await service.approve_loan(request, current_user.id)
        return loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/reject", response_model=LoanResponse)
async def reject_loan(
    request: LoanRejectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reject a loan application (Admin)"""
    # TODO: Add admin role check
    service = LoanService(db)
    try:
        loan = await service.reject_loan(request, current_user.id)
        return loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/{loan_id}/disburse", response_model=LoanResponse)
async def disburse_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Disburse an approved loan (Admin)"""
    # TODO: Add admin role check
    service = LoanService(db)
    try:
        loan = await service.disburse_loan(loan_id, current_user.id)
        return loan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Import datetime for response
from datetime import datetime
