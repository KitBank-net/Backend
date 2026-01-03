"""
OBP-Compatible Account Information Service (AIS) Router

Open Bank Project compatible endpoints for account data access.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.modules.openbanking.schemas import (
    OBPAccountList, OBPAccountDetail, OBPTransactionList, OBPBankInfo
)
from app.modules.openbanking.services import OpenBankingService

router = APIRouter(prefix="/obp/v5.1.0", tags=["open-banking-ais"])


async def validate_token(request: Request, db: AsyncSession) -> dict:
    """Extract and validate OAuth token from request"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split(" ")[1]
    
    service = OpenBankingService(db)
    token_record = await service.validate_access_token(token, required_scopes=["accounts"])
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {
        "user_id": token_record.user_id,
        "app_id": token_record.app_id,
        "consent_id": token_record.consent_id,
        "scopes": token_record.scopes
    }


# ============================================================
# Bank Information
# ============================================================

@router.get("/banks", response_model=list)
async def list_banks():
    """List available banks (OBP format)"""
    return [{
        "id": "kitbank",
        "short_name": "KitBank",
        "full_name": "KitBank Digital Banking",
        "logo": "https://kitbank.net/logo.png",
        "website": "https://kitbank.net"
    }]


@router.get("/banks/{bank_id}", response_model=OBPBankInfo)
async def get_bank(bank_id: str):
    """Get bank details"""
    if bank_id != "kitbank":
        raise HTTPException(status_code=404, detail="Bank not found")
    
    return OBPBankInfo()


# ============================================================
# Account Access
# ============================================================

@router.get("/my/accounts", response_model=OBPAccountList)
async def get_my_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get authenticated user's accounts.
    
    Requires OAuth2 token with 'accounts' scope.
    """
    token_info = await validate_token(request, db)
    service = OpenBankingService(db)
    
    # Get consent to check for account restrictions
    consent = None
    if token_info.get("consent_id"):
        consent = await service.get_consent(str(token_info["consent_id"]))
    
    accounts = await service.get_user_accounts_obp(token_info["user_id"], consent)
    
    return OBPAccountList(accounts=accounts)


@router.get("/banks/{bank_id}/accounts/{account_id}/account")
async def get_account_by_id(
    bank_id: str,
    account_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get account details.
    
    Requires OAuth2 token with 'accounts' scope.
    """
    if bank_id != "kitbank":
        raise HTTPException(status_code=404, detail="Bank not found")
    
    token_info = await validate_token(request, db)
    service = OpenBankingService(db)
    
    account = await service.get_account_detail_obp(int(account_id), token_info["user_id"])
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


@router.get("/banks/{bank_id}/accounts/{account_id}/balances")
async def get_account_balance(
    bank_id: str,
    account_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get account balance.
    
    Requires OAuth2 token with 'balances' scope.
    """
    if bank_id != "kitbank":
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Validate with balances scope
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = auth_header.split(" ")[1]
    service = OpenBankingService(db)
    token_record = await service.validate_access_token(token, required_scopes=["balances"])
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid token or insufficient scope")
    
    account = await service.get_account_detail_obp(int(account_id), token_record.user_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {
        "account_id": account_id,
        "bank_id": bank_id,
        "balances": [account.balance]
    }


# ============================================================
# Transaction Access
# ============================================================

@router.get("/banks/{bank_id}/accounts/{account_id}/transactions", response_model=OBPTransactionList)
async def get_account_transactions(
    bank_id: str,
    account_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get account transactions.
    
    Requires OAuth2 token with 'transactions' scope.
    """
    if bank_id != "kitbank":
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Validate with transactions scope
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = auth_header.split(" ")[1]
    service = OpenBankingService(db)
    token_record = await service.validate_access_token(token, required_scopes=["transactions"])
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid token or insufficient scope")
    
    transactions = await service.get_account_transactions_obp(
        int(account_id),
        token_record.user_id,
        limit=limit,
        offset=offset
    )
    
    return OBPTransactionList(transactions=transactions)


@router.get("/banks/{bank_id}/accounts/{account_id}/transactions/{transaction_id}")
async def get_transaction(
    bank_id: str,
    account_id: str,
    transaction_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific transaction"""
    if bank_id != "kitbank":
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Validate with transactions scope
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = auth_header.split(" ")[1]
    service = OpenBankingService(db)
    token_record = await service.validate_access_token(token, required_scopes=["transactions"])
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid token or insufficient scope")
    
    # Get all transactions and filter
    transactions = await service.get_account_transactions_obp(
        int(account_id),
        token_record.user_id,
        limit=1000
    )
    
    for txn in transactions:
        if txn.id == transaction_id:
            return txn
    
    raise HTTPException(status_code=404, detail="Transaction not found")
