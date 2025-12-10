from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_kyc_verified
from app.modules.users.models import User
from app.modules.accounts import schemas, services

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.post("", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: schemas.AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_kyc_verified)
):
    """
    Create a new account (checking/savings/business).
    
    - Requires KYC verification
    - Generates unique account number
    - Supports USD, EUR, GBP currencies
    """
    account = await services.AccountService.create_account(db, current_user.id, account_data)
    return account


@router.get("", response_model=List[schemas.AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all user accounts.
    
    - Returns all active accounts
    - Excludes closed accounts
    """
    accounts = await services.AccountService.get_user_accounts(db, current_user.id)
    return accounts


@router.get("/{account_id}", response_model=schemas.AccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get account details.
    """
    account = await services.AccountService.get_account(db, account_id, current_user.id)
    return account


@router.put("/{account_id}", response_model=schemas.AccountResponse)
async def update_account(
    account_id: int,
    settings: schemas.AccountSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update account settings.
    
    - Enable/disable overdraft
    - Enable/disable various transfer types
    """
    account = await services.AccountService.update_account_settings(
        db, account_id, current_user.id, settings
    )
    return account


@router.post("/{account_id}/close", status_code=status.HTTP_200_OK)
async def close_account(
    account_id: int,
    closure_data: schemas.AccountClosureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Request account closure.
    
    - Account must have zero balance or specify transfer account
    - Cannot be undone
    """
    await services.AccountService.close_account(db, account_id, current_user.id, closure_data)
    return {"message": "Account closed successfully"}


@router.get("/balances", response_model=schemas.AllBalancesResponse)
async def get_all_balances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all account balances.
    
    - Returns balances for all accounts
    - Includes total balance in USD
    """
    balances = await services.AccountService.get_all_balances(db, current_user.id)
    return balances


@router.get("/{account_id}/balance", response_model=schemas.BalanceResponse)
async def get_account_balance(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific account balance.
    
    - Returns current, available, and ledger balances
    """
    balance = await services.AccountService.get_account_balance(db, account_id, current_user.id)
    return balance


@router.put("/{account_id}/limits", response_model=schemas.AccountResponse)
async def update_transaction_limits(
    account_id: int,
    limits: schemas.TransactionLimitsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update transaction limits.
    
    - Daily transaction limit
    - Daily withdrawal limit
    - Monthly transaction limit
    """
    account = await services.AccountService.update_transaction_limits(
        db, account_id, current_user.id, limits
    )
    return account


@router.post("/{account_id}/statements", status_code=status.HTTP_200_OK)
async def generate_statement(
    account_id: int,
    statement_request: schemas.StatementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate account statement.
    
    - Supports PDF and CSV formats
    - Specify date range
    """
    statement = await services.AccountService.generate_statement(
        db, account_id, current_user.id, statement_request
    )
    return statement


@router.get("/{account_id}/statements/{year}/{month}", status_code=status.HTTP_200_OK)
async def get_monthly_statement(
    account_id: int,
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get monthly statement.
    """
    # TODO: Implement monthly statement retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Monthly statement retrieval not yet implemented"
    )


@router.get("/{account_id}/transactions", status_code=status.HTTP_200_OK)
async def get_account_transactions(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get account transactions.
    """
    # TODO: Implement transaction retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction retrieval not yet implemented"
    )


@router.post("/{account_id}/beneficiaries", status_code=status.HTTP_201_CREATED)
async def add_beneficiary(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add account beneficiary.
    """
    # TODO: Implement beneficiary management
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Beneficiary management not yet implemented"
    )


@router.get("/{account_id}/beneficiaries", status_code=status.HTTP_200_OK)
async def list_beneficiaries(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List beneficiaries.
    """
    # TODO: Implement beneficiary listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Beneficiary listing not yet implemented"
    )


@router.delete("/{account_id}/beneficiaries/{beneficiary_id}", status_code=status.HTTP_200_OK)
async def remove_beneficiary(
    account_id: int,
    beneficiary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove beneficiary.
    """
    # TODO: Implement beneficiary removal
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Beneficiary removal not yet implemented"
    )
