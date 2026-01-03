from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.transactions.schemas import (
    # Request schemas
    InternalTransferRequest,
    P2PTransferRequest,
    QRCodeGenerateRequest,
    QRPaymentRequest,
    BillPaymentRequest,
    MobileMoneyTransferRequest,
    InternationalTransferRequest,
    FeeCalculationRequest,
    TransactionHistoryFilter,
    # Response schemas
    TransactionResponse,
    TransactionListResponse,
    QRCodeResponse,
    FeeCalculationResponse,
    ExchangeRateResponse,
    # Enums
    TransactionType,
    TransactionStatus,
    Currency,
    TransactionChannel
)
from app.modules.transactions.services import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


# ============================================================
# Internal Transfer
# ============================================================

@router.post("/transfer/internal", response_model=TransactionResponse)
async def create_internal_transfer(
    request: InternalTransferRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Transfer between your own accounts"""
    service = TransactionService(db)
    try:
        transaction = await service.create_internal_transfer(
            request=request,
            user_id=current_user.id,
            channel=TransactionChannel.API,
            ip_address=http_request.client.host if http_request.client else None
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# P2P Transfer
# ============================================================

@router.post("/transfer/p2p", response_model=TransactionResponse)
async def create_p2p_transfer(
    request: P2PTransferRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Peer-to-peer transfer to another KitBank user"""
    service = TransactionService(db)
    try:
        transaction = await service.create_p2p_transfer(
            request=request,
            user_id=current_user.id,
            channel=TransactionChannel.API,
            ip_address=http_request.client.host if http_request.client else None
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# QR Payments
# ============================================================

@router.post("/qr/generate", response_model=QRCodeResponse)
async def generate_qr_code(
    request: QRCodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a QR code for receiving payments"""
    service = TransactionService(db)
    try:
        qr_code = await service.generate_qr_code(
            request=request,
            user_id=current_user.id
        )
        return qr_code
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/qr/pay", response_model=TransactionResponse)
async def pay_via_qr(
    request: QRPaymentRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pay by scanning a QR code"""
    service = TransactionService(db)
    try:
        transaction = await service.process_qr_payment(
            request=request,
            user_id=current_user.id,
            channel=TransactionChannel.MOBILE_APP,
            ip_address=http_request.client.host if http_request.client else None
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Bill Payment
# ============================================================

@router.post("/bills/pay", response_model=TransactionResponse)
async def pay_bill(
    request: BillPaymentRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pay a bill to a registered biller"""
    service = TransactionService(db)
    try:
        transaction = await service.create_bill_payment(
            request=request,
            user_id=current_user.id,
            channel=TransactionChannel.API,
            ip_address=http_request.client.host if http_request.client else None
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bills/billers")
async def get_billers(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of available billers"""
    # TODO: Implement biller registry
    billers = [
        {"biller_code": "KPLC", "biller_name": "Kenya Power", "category": "utilities"},
        {"biller_code": "SAFARICOM", "biller_name": "Safaricom Prepaid", "category": "telecom"},
        {"biller_code": "DSTV", "biller_name": "DSTV", "category": "entertainment"},
        {"biller_code": "ZUKU", "biller_name": "Zuku Fiber", "category": "internet"},
        {"biller_code": "NAIROBI_WATER", "biller_name": "Nairobi Water", "category": "utilities"},
    ]
    
    if category:
        billers = [b for b in billers if b["category"] == category]
    
    return {"billers": billers}


# ============================================================
# Mobile Money
# ============================================================

@router.post("/mobile-money/send", response_model=TransactionResponse)
async def send_mobile_money(
    request: MobileMoneyTransferRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send money to a mobile money wallet (M-Pesa, MTN, Airtel, etc.)"""
    service = TransactionService(db)
    try:
        transaction = await service.create_mobile_money_transfer(
            request=request,
            user_id=current_user.id,
            channel=TransactionChannel.API,
            ip_address=http_request.client.host if http_request.client else None
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mobile-money/providers")
async def get_mobile_money_providers(
    current_user: User = Depends(get_current_active_user)
):
    """Get list of supported mobile money providers"""
    providers = [
        {"code": "mpesa", "name": "M-Pesa", "countries": ["KE", "TZ"]},
        {"code": "mtn_momo", "name": "MTN Mobile Money", "countries": ["UG", "RW", "GH", "NG"]},
        {"code": "airtel_money", "name": "Airtel Money", "countries": ["KE", "UG", "TZ", "RW"]},
        {"code": "orange_money", "name": "Orange Money", "countries": ["SN", "CI", "CM"]},
        {"code": "tigo_pesa", "name": "Tigo Pesa", "countries": ["TZ"]},
    ]
    return {"providers": providers}


# ============================================================
# International Transfer
# ============================================================

@router.post("/transfer/international", response_model=TransactionResponse)
async def create_international_transfer(
    request: InternationalTransferRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send an international wire transfer (SWIFT)"""
    service = TransactionService(db)
    try:
        transaction = await service.create_international_transfer(
            request=request,
            user_id=current_user.id,
            channel=TransactionChannel.API,
            ip_address=http_request.client.host if http_request.client else None
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transfer/international/purpose-codes")
async def get_purpose_codes(
    current_user: User = Depends(get_current_active_user)
):
    """Get list of valid purpose codes for international transfers"""
    purpose_codes = [
        {"code": "FAM", "description": "Family maintenance/remittance"},
        {"code": "EDU", "description": "Education fees"},
        {"code": "MED", "description": "Medical expenses"},
        {"code": "SAL", "description": "Salary/wages"},
        {"code": "TRD", "description": "Trade payment"},
        {"code": "INV", "description": "Investment"},
        {"code": "GDS", "description": "Goods purchase"},
        {"code": "SRV", "description": "Service payment"},
        {"code": "TRV", "description": "Travel expenses"},
        {"code": "OTH", "description": "Other"},
    ]
    return {"purpose_codes": purpose_codes}


# ============================================================
# Transaction History
# ============================================================

@router.get("/", response_model=TransactionListResponse)
async def get_transactions(
    account_id: Optional[int] = None,
    transaction_type: Optional[TransactionType] = None,
    status: Optional[TransactionStatus] = None,
    currency: Optional[Currency] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    reference_code: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get transaction history with filters"""
    service = TransactionService(db)
    
    filters = TransactionHistoryFilter(
        account_id=account_id,
        transaction_type=transaction_type,
        status=status,
        currency=currency,
        min_amount=min_amount,
        max_amount=max_amount,
        reference_code=reference_code
    )
    
    transactions, total = await service.get_transactions(
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific transaction by ID"""
    service = TransactionService(db)
    transaction = await service.get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # TODO: Verify transaction belongs to user
    
    return transaction


@router.get("/reference/{reference_code}", response_model=TransactionResponse)
async def get_transaction_by_reference(
    reference_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a transaction by reference code"""
    service = TransactionService(db)
    transaction = await service.get_transaction_by_reference(reference_code)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # TODO: Verify transaction belongs to user
    
    return transaction


# ============================================================
# Fee Calculation
# ============================================================

@router.post("/fees/calculate", response_model=FeeCalculationResponse)
async def calculate_transaction_fee(
    request: FeeCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Calculate fee for a transaction type before executing"""
    service = TransactionService(db)
    return await service.calculate_fee(request)


# ============================================================
# Exchange Rates
# ============================================================

@router.get("/fx/rates", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    from_currency: Currency,
    to_currency: Currency,
    amount: Decimal = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get exchange rate for currency conversion"""
    service = TransactionService(db)
    return await service.get_exchange_rate(from_currency, to_currency, amount)


# ============================================================
# Account Transactions (Shortcut)
# ============================================================

@router.get("/account/{account_id}", response_model=TransactionListResponse)
async def get_account_transactions(
    account_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all transactions for a specific account"""
    service = TransactionService(db)
    
    filters = TransactionHistoryFilter(account_id=account_id)
    
    transactions, total = await service.get_transactions(
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
