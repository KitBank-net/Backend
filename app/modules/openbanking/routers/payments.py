"""
Payment Initiation Service (PIS) Router

PSD2-compliant payment initiation endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import secrets

from app.core.database import get_db
from app.modules.openbanking.schemas import (
    PaymentInitiationRequest, PaymentInitiationResponse, PaymentStatusResponse
)
from app.modules.openbanking.services import OpenBankingService
from app.modules.accounts.models import Account
from app.modules.transactions.models import Transaction, TransactionType, TransactionStatus

router = APIRouter(prefix="/payments", tags=["open-banking-pis"])


async def validate_payment_token(request: Request, db: AsyncSession) -> dict:
    """Validate OAuth token with payments scope"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split(" ")[1]
    
    service = OpenBankingService(db)
    token_record = await service.validate_access_token(token, required_scopes=["payments"])
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Check consent has PIS permission
    if token_record.consent_id:
        consent = await service.get_consent(str(token_record.consent_id))
        if consent and not consent.payment_initiation:
            raise HTTPException(status_code=403, detail="Payment initiation not authorized")
    
    return {
        "user_id": token_record.user_id,
        "app_id": token_record.app_id,
        "consent_id": token_record.consent_id
    }


@router.post("", response_model=PaymentInitiationResponse)
async def initiate_payment(
    data: PaymentInitiationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate a payment.
    
    Third-party apps can initiate payments on behalf of users
    who have granted PIS consent.
    
    The payment requires Strong Customer Authentication (SCA)
    before execution.
    """
    token_info = await validate_payment_token(request, db)
    
    from sqlalchemy import select
    
    # Verify debtor account belongs to user
    result = await db.execute(
        select(Account).where(
            Account.id == int(data.debtor_account),
            Account.user_id == token_info["user_id"]
        )
    )
    debtor_account = result.scalar_one_or_none()
    
    if not debtor_account:
        raise HTTPException(status_code=400, detail="Invalid debtor account")
    
    # Check balance
    if debtor_account.available_balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Create pending transaction
    payment_id = secrets.token_urlsafe(16)
    
    transaction = Transaction(
        reference=f"PIS-{payment_id}",
        transaction_type=TransactionType.EXTERNAL_TRANSFER,
        source_account_id=debtor_account.id,
        amount=data.amount,
        currency=debtor_account.currency,
        recipient_account_number=data.creditor_account,
        recipient_name=data.creditor_name,
        description=data.description or "Open Banking Payment",
        status=TransactionStatus.PENDING,
        requires_approval=True,  # SCA required
        internal_notes=f"PIS initiated by app_id={token_info['app_id']}"
    )
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    # Generate SCA authorization URL
    base_url = "https://kitbank.net"
    auth_url = f"{base_url}/payments/{transaction.id}/authorize"
    
    return PaymentInitiationResponse(
        payment_id=str(transaction.id),
        status="pending",
        created_at=transaction.created_at,
        debtor_account=data.debtor_account,
        creditor_account=data.creditor_account,
        creditor_name=data.creditor_name,
        amount=data.amount,
        currency=data.currency,
        authorization_url=auth_url
    )


@router.get("/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment status.
    
    Check the status of a previously initiated payment.
    """
    token_info = await validate_payment_token(request, db)
    
    from sqlalchemy import select
    
    # Find transaction
    result = await db.execute(
        select(Transaction).where(Transaction.id == int(payment_id))
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Verify the user has access via their account
    acc_result = await db.execute(
        select(Account).where(
            Account.id == transaction.source_account_id,
            Account.user_id == token_info["user_id"]
        )
    )
    if not acc_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    return PaymentStatusResponse(
        payment_id=str(transaction.id),
        status=transaction.status.value,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        completed_at=transaction.completed_at,
        failure_reason=transaction.failure_reason
    )


@router.post("/{payment_id}/authorize")
async def authorize_payment(
    payment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authorize a payment (SCA).
    
    User authorizes the payment after Strong Customer Authentication.
    """
    token_info = await validate_payment_token(request, db)
    
    from sqlalchemy import select
    
    # Find transaction
    result = await db.execute(
        select(Transaction).where(Transaction.id == int(payment_id))
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if transaction.status != TransactionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Payment cannot be authorized")
    
    # Verify ownership
    acc_result = await db.execute(
        select(Account).where(
            Account.id == transaction.source_account_id,
            Account.user_id == token_info["user_id"]
        )
    )
    account = acc_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # TODO: In a real implementation, this would:
    # 1. Verify SCA (biometric, OTP, etc.)
    # 2. Process the actual payment
    # 3. Update balances
    
    # For now, mark as processing
    transaction.status = TransactionStatus.PROCESSING
    transaction.approved_at = datetime.utcnow()
    
    # Deduct from source account
    account.current_balance -= transaction.amount
    account.available_balance -= transaction.amount
    
    # Mark complete (in production, this would be async)
    transaction.status = TransactionStatus.COMPLETED
    transaction.completed_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "payment_id": payment_id,
        "status": "completed",
        "message": "Payment authorized and executed"
    }


@router.post("/{payment_id}/cancel")
async def cancel_payment(
    payment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a pending payment.
    
    Only pending payments can be cancelled.
    """
    token_info = await validate_payment_token(request, db)
    
    from sqlalchemy import select
    
    result = await db.execute(
        select(Transaction).where(Transaction.id == int(payment_id))
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if transaction.status != TransactionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending payments can be cancelled")
    
    # Verify ownership
    acc_result = await db.execute(
        select(Account).where(
            Account.id == transaction.source_account_id,
            Account.user_id == token_info["user_id"]
        )
    )
    if not acc_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")
    
    transaction.status = TransactionStatus.CANCELLED
    transaction.failed_at = datetime.utcnow()
    transaction.failure_reason = "Cancelled by user"
    
    await db.commit()
    
    return {
        "payment_id": payment_id,
        "status": "cancelled",
        "message": "Payment cancelled"
    }
