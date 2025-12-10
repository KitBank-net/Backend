from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal
import random
import string

from app.modules.accounts.models import Account, AccountType, Currency, AccountStatusEnum, AccountTier
from app.modules.accounts import schemas
from app.modules.users.models import User, KYCStatus


class AccountService:
    """Service layer for account management operations"""
    
    @staticmethod
    def generate_account_number() -> str:
        """Generate unique 12-digit account number"""
        return ''.join(random.choices(string.digits, k=12))
    
    @staticmethod
    def generate_routing_number() -> str:
        """Generate 9-digit routing number (US)"""
        return ''.join(random.choices(string.digits, k=9))
    
    @staticmethod
    async def create_account(
        db: AsyncSession,
        user_id: int,
        account_data: schemas.AccountCreateRequest
    ) -> Account:
        """Create a new account for user"""
        
        # Check if user exists and is KYC verified
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.kyc_status != KYCStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="KYC verification required to create an account"
            )
        
        # Generate unique account number
        account_number = AccountService.generate_account_number()
        
        # Check if account number already exists (very unlikely but possible)
        while True:
            result = await db.execute(
                select(Account).where(Account.account_number == account_number)
            )
            if not result.scalar_one_or_none():
                break
            account_number = AccountService.generate_account_number()
        
        # Create account
        account = Account(
            user_id=user_id,
            account_number=account_number,
            routing_number=AccountService.generate_routing_number(),
            account_type=account_data.account_type,
            currency=account_data.currency,
            account_tier=account_data.account_tier or AccountTier.BASIC,
            account_status=AccountStatusEnum.ACTIVE
        )
        
        db.add(account)
        await db.commit()
        await db.refresh(account)
        
        return account
    
    @staticmethod
    async def get_user_accounts(db: AsyncSession, user_id: int) -> List[Account]:
        """Get all accounts for a user"""
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.user_id == user_id,
                    Account.account_status != AccountStatusEnum.CLOSED
                )
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_account(db: AsyncSession, account_id: int, user_id: int) -> Account:
        """Get specific account"""
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.id == account_id,
                    Account.user_id == user_id
                )
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        return account
    
    @staticmethod
    async def update_account_settings(
        db: AsyncSession,
        account_id: int,
        user_id: int,
        settings: schemas.AccountSettingsUpdate
    ) -> Account:
        """Update account settings"""
        account = await AccountService.get_account(db, account_id, user_id)
        
        # Update fields
        update_data = settings.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        
        await db.commit()
        await db.refresh(account)
        
        return account
    
    @staticmethod
    async def update_transaction_limits(
        db: AsyncSession,
        account_id: int,
        user_id: int,
        limits: schemas.TransactionLimitsUpdate
    ) -> Account:
        """Update transaction limits"""
        account = await AccountService.get_account(db, account_id, user_id)
        
        # Update limits
        update_data = limits.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        
        await db.commit()
        await db.refresh(account)
        
        return account
    
    @staticmethod
    async def get_account_balance(
        db: AsyncSession,
        account_id: int,
        user_id: int
    ) -> schemas.BalanceResponse:
        """Get account balance"""
        account = await AccountService.get_account(db, account_id, user_id)
        
        return schemas.BalanceResponse(
            account_id=account.id,
            account_number=account.account_number,
            current_balance=account.current_balance,
            available_balance=account.available_balance,
            ledger_balance=account.ledger_balance,
            currency=account.currency.value
        )
    
    @staticmethod
    async def get_all_balances(
        db: AsyncSession,
        user_id: int
    ) -> schemas.AllBalancesResponse:
        """Get all account balances for user"""
        accounts = await AccountService.get_user_accounts(db, user_id)
        
        balances = []
        total_usd = Decimal('0.00')
        
        for account in accounts:
            balance = schemas.BalanceResponse(
                account_id=account.id,
                account_number=account.account_number,
                current_balance=account.current_balance,
                available_balance=account.available_balance,
                ledger_balance=account.ledger_balance,
                currency=account.currency.value
            )
            balances.append(balance)
            
            # Convert to USD for total (simplified - would need exchange rates in production)
            if account.currency == Currency.USD:
                total_usd += account.current_balance
            # TODO: Add currency conversion for EUR, GBP
        
        return schemas.AllBalancesResponse(
            accounts=balances,
            total_balance_usd=total_usd
        )
    
    @staticmethod
    async def close_account(
        db: AsyncSession,
        account_id: int,
        user_id: int,
        closure_data: schemas.AccountClosureRequest
    ) -> bool:
        """Close an account"""
        account = await AccountService.get_account(db, account_id, user_id)
        
        # Check if account has balance
        if account.current_balance > 0:
            if not closure_data.transfer_remaining_balance_to:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account has remaining balance. Please specify transfer account or withdraw funds."
                )
            
            # TODO: Transfer balance to specified account
        
        # Close account
        account.account_status = AccountStatusEnum.CLOSED
        account.closed_date = date.today()
        account.closure_reason = closure_data.reason
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def generate_statement(
        db: AsyncSession,
        account_id: int,
        user_id: int,
        statement_request: schemas.StatementRequest
    ) -> dict:
        """Generate account statement"""
        account = await AccountService.get_account(db, account_id, user_id)
        
        # TODO: Implement actual statement generation with transactions
        # For now, return basic info
        
        return {
            "account_number": account.account_number,
            "statement_period": {
                "start_date": statement_request.start_date,
                "end_date": statement_request.end_date
            },
            "opening_balance": account.current_balance,
            "closing_balance": account.current_balance,
            "transactions": [],  # TODO: Get transactions for period
            "format": statement_request.format
        }
