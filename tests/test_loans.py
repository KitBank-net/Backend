"""
Unit tests for Loan Service
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.modules.loans.services import LoanService
from app.modules.loans.models import LoanStatus, RepaymentFrequency
from app.modules.loans.schemas import (
    LoanApplicationRequest, LoanCalculatorRequest, LoanEligibilityRequest
)


class TestLoanCalculations:
    """Tests for loan calculation methods"""
    
    @pytest.mark.unit
    def test_calculate_monthly_payment(self):
        """Test monthly payment calculation"""
        service = LoanService(None)
        
        # $10,000 loan at 12% for 12 months
        payment = service._calculate_monthly_payment(
            principal=Decimal("10000.00"),
            annual_rate=Decimal("12.00"),
            term_months=12
        )
        
        # Should be approximately $888.49
        assert payment > Decimal("880.00")
        assert payment < Decimal("900.00")
    
    @pytest.mark.unit
    def test_calculate_monthly_payment_zero_interest(self):
        """Test monthly payment with zero interest"""
        service = LoanService(None)
        
        payment = service._calculate_monthly_payment(
            principal=Decimal("1200.00"),
            annual_rate=Decimal("0.00"),
            term_months=12
        )
        
        assert payment == Decimal("100.00")
    
    @pytest.mark.unit
    def test_generate_amortization_schedule(self):
        """Test amortization schedule generation"""
        service = LoanService(None)
        
        schedule = service._generate_amortization_schedule(
            principal=Decimal("10000.00"),
            annual_rate=Decimal("12.00"),
            term_months=12,
            start_date=date.today() + timedelta(days=30),
            frequency=RepaymentFrequency.MONTHLY
        )
        
        assert len(schedule) == 12
        assert schedule[0]["payment_number"] == 1
        assert schedule[-1]["payment_number"] == 12
        
        # Final balance should be 0 or very close
        assert schedule[-1]["balance_after"] <= Decimal("0.01")
        
        # Total principal paid should equal original principal
        total_principal = sum(p["principal_component"] for p in schedule)
        assert abs(total_principal - Decimal("10000.00")) < Decimal("0.01")
    
    @pytest.mark.unit
    def test_loan_calculator(self):
        """Test loan calculator response"""
        service = LoanService(None)
        
        request = LoanCalculatorRequest(
            principal=Decimal("5000.00"),
            interest_rate=Decimal("15.00"),
            term_months=24,
            repayment_frequency=RepaymentFrequency.MONTHLY
        )
        
        response = service.calculate_loan(request)
        
        assert response.principal == Decimal("5000.00")
        assert response.interest_rate == Decimal("15.00")
        assert response.term_months == 24
        assert response.monthly_payment > Decimal("0")
        assert response.total_interest > Decimal("0")
        assert response.total_repayment == response.principal + response.total_interest
        assert len(response.amortization_schedule) == 24


class TestLoanApplication:
    """Tests for loan application"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_apply_for_loan_success(self, db_session, test_user, test_account, test_loan_product):
        """Test successful loan application"""
        service = LoanService(db_session)
        
        request = LoanApplicationRequest(
            product_id=test_loan_product.id,
            account_id=test_account.id,
            requested_amount=Decimal("5000.00"),
            term_months=12,
            purpose="Home renovation"
        )
        
        loan = await service.apply_for_loan(test_user.id, request)
        
        assert loan is not None
        assert loan.status == LoanStatus.DRAFT
        assert loan.requested_amount == Decimal("5000.00")
        assert loan.term_months == 12
        assert loan.reference_number.startswith("LN-")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_apply_for_loan_amount_too_low(self, db_session, test_user, test_account, test_loan_product):
        """Test loan application with amount below minimum"""
        service = LoanService(db_session)
        
        request = LoanApplicationRequest(
            product_id=test_loan_product.id,
            account_id=test_account.id,
            requested_amount=Decimal("100.00"),  # Below min of 1000
            term_months=12,
            purpose="Test"
        )
        
        with pytest.raises(ValueError, match="Minimum loan amount"):
            await service.apply_for_loan(test_user.id, request)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_apply_for_loan_amount_too_high(self, db_session, test_user, test_account, test_loan_product):
        """Test loan application with amount above maximum"""
        service = LoanService(db_session)
        
        request = LoanApplicationRequest(
            product_id=test_loan_product.id,
            account_id=test_account.id,
            requested_amount=Decimal("100000.00"),  # Above max of 50000
            term_months=12,
            purpose="Test"
        )
        
        with pytest.raises(ValueError, match="Maximum loan amount"):
            await service.apply_for_loan(test_user.id, request)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_submit_loan_application(self, db_session, test_user, test_account, test_loan_product):
        """Test submitting a loan application"""
        service = LoanService(db_session)
        
        # First create a loan
        request = LoanApplicationRequest(
            product_id=test_loan_product.id,
            account_id=test_account.id,
            requested_amount=Decimal("5000.00"),
            term_months=12,
            purpose="Test"
        )
        
        loan = await service.apply_for_loan(test_user.id, request)
        assert loan.status == LoanStatus.DRAFT
        
        # Submit it
        submitted = await service.submit_loan_application(loan.id, test_user.id)
        
        assert submitted.status == LoanStatus.SUBMITTED
        assert submitted.submitted_at is not None


class TestLoanEligibility:
    """Tests for loan eligibility checks"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_check_eligibility_eligible(self, db_session, test_user, test_loan_product):
        """Test eligibility check for eligible user"""
        service = LoanService(db_session)
        
        request = LoanEligibilityRequest(
            product_id=test_loan_product.id,
            requested_amount=Decimal("5000.00"),
            term_months=12,
            monthly_income=Decimal("5000.00")
        )
        
        response = await service.check_eligibility(test_user.id, request)
        
        assert response.eligible is True
        assert response.estimated_monthly_payment > Decimal("0")
    
    @pytest.mark.integration  
    @pytest.mark.asyncio
    async def test_check_eligibility_amount_too_high(self, db_session, test_user, test_loan_product):
        """Test eligibility check with too high amount"""
        service = LoanService(db_session)
        
        request = LoanEligibilityRequest(
            product_id=test_loan_product.id,
            requested_amount=Decimal("100000.00"),  # Exceeds max
            term_months=12
        )
        
        response = await service.check_eligibility(test_user.id, request)
        
        assert response.eligible is False
        assert any("maximum" in reason.lower() for reason in response.reasons)


class TestLoanSummary:
    """Tests for loan summary"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_loan_summary_empty(self, db_session, test_user):
        """Test loan summary with no loans"""
        service = LoanService(db_session)
        
        summary = await service.get_loan_summary(test_user.id)
        
        assert summary.total_loans == 0
        assert summary.active_loans == 0
        assert summary.total_borrowed == Decimal("0")
        assert summary.total_outstanding == Decimal("0")
