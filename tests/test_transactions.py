"""
Unit tests for Transaction Service
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.transactions.services import TransactionService
from app.modules.transactions.models import TransactionType, TransactionStatus, Currency
from app.modules.transactions.schemas import (
    InternalTransferRequest, P2PTransferRequest, FeeCalculationRequest
)


class TestTransactionService:
    """Tests for TransactionService"""
    
    @pytest.mark.unit
    def test_generate_reference(self):
        """Test transaction reference generation"""
        service = TransactionService(None)
        ref = service._generate_reference()
        
        assert ref.startswith("TXN-")
        assert len(ref) == 16  # TXN- + 12 chars
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_fee_no_config(self, db_session):
        """Test fee calculation when no config exists"""
        service = TransactionService(db_session)
        
        fee, breakdown = await service._calculate_fee(
            TransactionType.TRANSFER,
            Decimal("100.00"),
            Currency.USD
        )
        
        assert fee == Decimal("0.00")
        assert breakdown["flat_fee"] == 0
        assert breakdown["percentage_fee"] == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_account_balance_sufficient(self, db_session, test_account):
        """Test balance validation with sufficient funds"""
        service = TransactionService(db_session)
        
        is_valid = await service._validate_account_balance(
            test_account,
            Decimal("100.00")
        )
        
        assert is_valid is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_account_balance_insufficient(self, db_session, test_account):
        """Test balance validation with insufficient funds"""
        service = TransactionService(db_session)
        
        is_valid = await service._validate_account_balance(
            test_account,
            Decimal("999999.00")  # More than available
        )
        
        assert is_valid is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_account_balance_credit(self, db_session, test_account):
        """Test crediting account balance"""
        service = TransactionService(db_session)
        original_balance = test_account.current_balance
        
        before, after = await service._update_account_balance(
            test_account,
            Decimal("500.00"),
            is_credit=True
        )
        
        assert before == original_balance
        assert after == original_balance + Decimal("500.00")
        assert test_account.current_balance == after
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_account_balance_debit(self, db_session, test_account):
        """Test debiting account balance"""
        service = TransactionService(db_session)
        original_balance = test_account.current_balance
        
        before, after = await service._update_account_balance(
            test_account,
            Decimal("500.00"),
            is_credit=False
        )
        
        assert before == original_balance
        assert after == original_balance - Decimal("500.00")
        assert test_account.current_balance == after


class TestInternalTransfer:
    """Tests for internal transfers"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_internal_transfer_success(self, db_session, test_user, test_account):
        """Test successful internal transfer"""
        # Create second account for transfer
        from app.modules.accounts.models import Account, AccountType, Currency as AccCurrency, AccountTier, AccountStatusEnum
        from datetime import date
        
        dest_account = Account(
            user_id=test_user.id,
            account_number="100000000002",
            routing_number="123456789",
            account_type=AccountType.SAVINGS,
            currency=AccCurrency.USD,
            account_tier=AccountTier.BASIC,
            current_balance=Decimal("5000.00"),
            available_balance=Decimal("5000.00"),
            ledger_balance=Decimal("5000.00"),
            overdraft_limit=Decimal("0.00"),
            overdraft_enabled=False,
            interest_rate=Decimal("0.02"),
            minimum_balance=Decimal("0.00"),
            daily_transaction_limit=Decimal("10000.00"),
            daily_withdrawal_limit=Decimal("5000.00"),
            monthly_transaction_limit=Decimal("100000.00"),
            check_writing_enabled=False,
            wire_transfer_enabled=True,
            ach_transfer_enabled=True,
            international_transfer_enabled=False,
            direct_deposit_enabled=True,
            bill_pay_enabled=False,
            debit_card_enabled=False,
            account_status=AccountStatusEnum.ACTIVE,
            opened_date=date.today()
        )
        db_session.add(dest_account)
        await db_session.commit()
        await db_session.refresh(dest_account)
        
        service = TransactionService(db_session)
        request = InternalTransferRequest(
            source_account_id=test_account.id,
            destination_account_id=dest_account.id,
            amount=Decimal("100.00"),
            currency=Currency.USD,
            description="Test transfer"
        )
        
        transaction = await service.create_internal_transfer(
            request=request,
            user_id=test_user.id
        )
        
        assert transaction is not None
        assert transaction.amount == Decimal("100.00")
        assert transaction.status == TransactionStatus.COMPLETED
        assert transaction.transaction_type == TransactionType.TRANSFER
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_internal_transfer_insufficient_funds(self, db_session, test_user, test_account):
        """Test internal transfer with insufficient funds"""
        from app.modules.accounts.models import Account, AccountType, Currency as AccCurrency, AccountTier, AccountStatusEnum
        from datetime import date
        
        dest_account = Account(
            user_id=test_user.id,
            account_number="100000000003",
            routing_number="123456789",
            account_type=AccountType.SAVINGS,
            currency=AccCurrency.USD,
            account_tier=AccountTier.BASIC,
            current_balance=Decimal("0.00"),
            available_balance=Decimal("0.00"),
            ledger_balance=Decimal("0.00"),
            overdraft_limit=Decimal("0.00"),
            overdraft_enabled=False,
            interest_rate=Decimal("0.02"),
            minimum_balance=Decimal("0.00"),
            daily_transaction_limit=Decimal("10000.00"),
            daily_withdrawal_limit=Decimal("5000.00"),
            monthly_transaction_limit=Decimal("100000.00"),
            check_writing_enabled=False,
            wire_transfer_enabled=True,
            ach_transfer_enabled=True,
            international_transfer_enabled=False,
            direct_deposit_enabled=True,
            bill_pay_enabled=False,
            debit_card_enabled=False,
            account_status=AccountStatusEnum.ACTIVE,
            opened_date=date.today()
        )
        db_session.add(dest_account)
        await db_session.commit()
        await db_session.refresh(dest_account)
        
        # Set source account to low balance
        test_account.available_balance = Decimal("10.00")
        await db_session.commit()
        
        service = TransactionService(db_session)
        request = InternalTransferRequest(
            source_account_id=test_account.id,
            destination_account_id=dest_account.id,
            amount=Decimal("1000.00"),  # More than available
            currency=Currency.USD
        )
        
        with pytest.raises(ValueError, match="Insufficient funds"):
            await service.create_internal_transfer(
                request=request,
                user_id=test_user.id
            )


class TestFeeCalculation:
    """Tests for fee calculation"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_calculate_fee_endpoint(self, db_session):
        """Test fee calculation service"""
        service = TransactionService(db_session)
        
        request = FeeCalculationRequest(
            transaction_type=TransactionType.P2P,
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
        response = await service.calculate_fee(request)
        
        assert response.amount == Decimal("100.00")
        assert response.fee_amount >= Decimal("0.00")
        assert response.total_amount == response.amount + response.fee_amount
