"""
Admin reports and analytics endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.modules.users.models import User
from app.modules.accounts.models import Account
from app.modules.transactions.models import Transaction, TransactionStatus
from app.modules.loans.models import Loan, LoanPayment, LoanStatus

router = APIRouter(prefix="/reports", tags=["admin-reports"])


@router.get("/overview")
async def get_overview_report(db: AsyncSession = Depends(get_db)):
    """Get overall platform overview"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    
    # Users
    total_users = await db.execute(select(func.count(User.id)))
    new_users_today = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_users_week = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    new_users_month = await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )
    
    # Transactions
    txn_today = await db.execute(
        select(func.count(Transaction.id), func.sum(Transaction.amount))
        .where(and_(
            Transaction.created_at >= today_start,
            Transaction.status == TransactionStatus.COMPLETED
        ))
    )
    txn_week = await db.execute(
        select(func.count(Transaction.id), func.sum(Transaction.amount))
        .where(and_(
            Transaction.created_at >= week_start,
            Transaction.status == TransactionStatus.COMPLETED
        ))
    )
    
    # Accounts & Balance
    total_balance = await db.execute(select(func.sum(Account.current_balance)))
    
    today_data = txn_today.one()
    week_data = txn_week.one()
    
    return {
        "users": {
            "total": total_users.scalar() or 0,
            "new_today": new_users_today.scalar() or 0,
            "new_this_week": new_users_week.scalar() or 0,
            "new_this_month": new_users_month.scalar() or 0
        },
        "transactions": {
            "today_count": today_data[0] or 0,
            "today_volume": float(today_data[1] or 0),
            "week_count": week_data[0] or 0,
            "week_volume": float(week_data[1] or 0)
        },
        "total_assets": float(total_balance.scalar() or 0)
    }


@router.get("/users")
async def get_user_report(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get user registration report"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Total registrations in period
    total = await db.execute(
        select(func.count(User.id)).where(
            and_(User.created_at >= start_dt, User.created_at <= end_dt)
        )
    )
    
    # By account status
    status_result = await db.execute(
        select(User.account_status, func.count(User.id))
        .where(and_(User.created_at >= start_dt, User.created_at <= end_dt))
        .group_by(User.account_status)
    )
    by_status = {str(s): c for s, c in status_result.all()}
    
    # By KYC status
    kyc_result = await db.execute(
        select(User.kyc_status, func.count(User.id))
        .where(and_(User.created_at >= start_dt, User.created_at <= end_dt))
        .group_by(User.kyc_status)
    )
    by_kyc = {str(s): c for s, c in kyc_result.all()}
    
    # Daily breakdown
    daily_result = await db.execute(
        select(
            func.date(User.created_at).label('date'),
            func.count(User.id)
        )
        .where(and_(User.created_at >= start_dt, User.created_at <= end_dt))
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    daily = [{"date": str(d), "count": c} for d, c in daily_result.all()]
    
    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "total_registrations": total.scalar() or 0,
        "by_account_status": by_status,
        "by_kyc_status": by_kyc,
        "daily_breakdown": daily
    }


@router.get("/transactions")
async def get_transaction_report(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get transaction summary report"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Total count and volume
    totals = await db.execute(
        select(func.count(Transaction.id), func.sum(Transaction.amount))
        .where(and_(
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
            Transaction.status == TransactionStatus.COMPLETED
        ))
    )
    total_data = totals.one()
    
    # By type
    type_result = await db.execute(
        select(
            Transaction.transaction_type,
            func.count(Transaction.id),
            func.sum(Transaction.amount)
        )
        .where(and_(Transaction.created_at >= start_dt, Transaction.created_at <= end_dt))
        .group_by(Transaction.transaction_type)
    )
    by_type = {str(t): {"count": c, "volume": float(v or 0)} for t, c, v in type_result.all()}
    
    # By status
    status_result = await db.execute(
        select(Transaction.status, func.count(Transaction.id))
        .where(and_(Transaction.created_at >= start_dt, Transaction.created_at <= end_dt))
        .group_by(Transaction.status)
    )
    by_status = {str(s): c for s, c in status_result.all()}
    
    # Daily trend
    daily_result = await db.execute(
        select(
            func.date(Transaction.created_at).label('date'),
            func.count(Transaction.id),
            func.sum(Transaction.amount)
        )
        .where(and_(
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
            Transaction.status == TransactionStatus.COMPLETED
        ))
        .group_by(func.date(Transaction.created_at))
        .order_by(func.date(Transaction.created_at))
    )
    daily = [{"date": str(d), "count": c, "volume": float(v or 0)} for d, c, v in daily_result.all()]
    
    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "total_transactions": total_data[0] or 0,
        "total_volume": float(total_data[1] or 0),
        "by_type": by_type,
        "by_status": by_status,
        "daily_trend": daily
    }


@router.get("/loans")
async def get_loan_report(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get loan summary report"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Applications
    apps = await db.execute(
        select(func.count(Loan.id), func.sum(Loan.requested_amount))
        .where(and_(Loan.created_at >= start_dt, Loan.created_at <= end_dt))
    )
    app_data = apps.one()
    
    # Approvals
    approved = await db.execute(
        select(func.count(Loan.id), func.sum(Loan.approved_amount))
        .where(and_(Loan.approved_at >= start_dt, Loan.approved_at <= end_dt))
    )
    approved_data = approved.one()
    
    # Disbursements
    disbursed = await db.execute(
        select(func.count(Loan.id), func.sum(Loan.disbursed_amount))
        .where(and_(Loan.disbursed_at >= start_dt, Loan.disbursed_at <= end_dt))
    )
    disbursed_data = disbursed.one()
    
    # By status
    status_result = await db.execute(
        select(Loan.status, func.count(Loan.id))
        .where(and_(Loan.created_at >= start_dt, Loan.created_at <= end_dt))
        .group_by(Loan.status)
    )
    by_status = {str(s): c for s, c in status_result.all()}
    
    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "applications": {
            "count": app_data[0] or 0,
            "amount": float(app_data[1] or 0)
        },
        "approvals": {
            "count": approved_data[0] or 0,
            "amount": float(approved_data[1] or 0)
        },
        "disbursements": {
            "count": disbursed_data[0] or 0,
            "amount": float(disbursed_data[1] or 0)
        },
        "by_status": by_status
    }


@router.get("/revenue")
async def get_revenue_report(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get revenue report from fees and interest"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Transaction fees
    fee_result = await db.execute(
        select(func.sum(Transaction.fee_amount))
        .where(and_(
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
            Transaction.status == TransactionStatus.COMPLETED
        ))
    )
    total_fees = fee_result.scalar() or 0
    
    # Fees by type
    fees_by_type = await db.execute(
        select(Transaction.transaction_type, func.sum(Transaction.fee_amount))
        .where(and_(
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
            Transaction.status == TransactionStatus.COMPLETED
        ))
        .group_by(Transaction.transaction_type)
    )
    by_type = {str(t): float(f or 0) for t, f in fees_by_type.all()}
    
    # Loan interest revenue
    interest_result = await db.execute(
        select(func.sum(LoanPayment.paid_interest))
        .where(and_(
            LoanPayment.paid_at >= start_dt,
            LoanPayment.paid_at <= end_dt
        ))
    )
    total_interest = interest_result.scalar() or 0
    
    # Late fees
    late_fees = await db.execute(
        select(func.sum(LoanPayment.late_fee))
        .where(and_(
            LoanPayment.paid_at >= start_dt,
            LoanPayment.paid_at <= end_dt
        ))
    )
    total_late_fees = late_fees.scalar() or 0
    
    total_revenue = float(total_fees) + float(total_interest) + float(total_late_fees)
    
    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "transaction_fees": {
            "total": float(total_fees),
            "by_type": by_type
        },
        "loan_interest": float(total_interest),
        "late_fees": float(total_late_fees),
        "total_revenue": total_revenue
    }


@router.get("/accounts")
async def get_account_report(db: AsyncSession = Depends(get_db)):
    """Get account summary report"""
    # Total accounts
    total = await db.execute(select(func.count(Account.id)))
    
    # By type
    type_result = await db.execute(
        select(Account.account_type, func.count(Account.id), func.sum(Account.current_balance))
        .group_by(Account.account_type)
    )
    by_type = {str(t): {"count": c, "balance": float(b or 0)} for t, c, b in type_result.all()}
    
    # By status
    status_result = await db.execute(
        select(Account.account_status, func.count(Account.id))
        .group_by(Account.account_status)
    )
    by_status = {str(s): c for s, c in status_result.all()}
    
    # Total balance
    balance = await db.execute(select(func.sum(Account.current_balance)))
    
    # Average balance
    avg_balance = await db.execute(select(func.avg(Account.current_balance)))
    
    return {
        "total_accounts": total.scalar() or 0,
        "total_balance": float(balance.scalar() or 0),
        "average_balance": float(avg_balance.scalar() or 0),
        "by_type": by_type,
        "by_status": by_status
    }
