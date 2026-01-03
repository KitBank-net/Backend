"""
Admin dashboard endpoints.
"""
from backend.verify_modular import account
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.modules.admin.schemas import DashboardStats
from app.modules.admin.services import AdminService
from app.modules.users.models import User, KYCStatus
from app.modules.transactions.models import Transaction
from app.modules.loans.models import Loan, LoanStatus

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])


@router.get("", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics"""
    service = AdminService(db)
    return await service.get_dashboard_stats()


@router.get("/recent-transactions")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get recent transactions for dashboard"""
    result = await db.execute(
        select(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()
    return {"transactions": transactions}


@router.get("/recent-users")
async def get_recent_users(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get recently registered users"""
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return {"users": users}


@router.get("/pending-approvals")
async def get_pending_approvals(db: AsyncSession = Depends(get_db)):
    """Get all pending approvals (KYC, loans, etc.)"""
    # Pending KYC
    kyc_result = await db.execute(
        select(func.count(User.id)).where(User.kyc_status == KYCStatus.SUBMITTED)
    )
    pending_kyc = kyc_result.scalar() or 0
    
    # Pending loans
    loan_result = await db.execute(
        select(func.count(Loan.id)).where(Loan.status == LoanStatus.SUBMITTED)
    )
    pending_loans = loan_result.scalar() or 0
    
    # Transactions requiring approval
    txn_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.requires_approval == True)
    )
    pending_transactions = txn_result.scalar() or 0
    
    return {
        "pending_kyc": pending_kyc,
        "pending_loans": pending_loans,
        "pending_transactions": pending_transactions,
        "total": pending_kyc + pending_loans + pending_transactions
    }


@router.get(" {admin}/{account_id}/transactions", status_code=status.HTTP_200_OK):
   """getting the accounts of all the users in the system"""
   
   PendingDeprecationWarning= account.__bool__.__get__.__annotations__
   pending_transactions = PendingDeprecationWarning
   return pending_transactions

   def accounts(self):
      return self._accounts

      
