from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from dateutil.relativedelta import relativedelta
import uuid

from app.modules.loans.models import (
    Loan, LoanProduct, LoanPayment, LoanDocument,
    LoanType, LoanStatus, RepaymentFrequency, PaymentStatus, CollateralType
)
from app.modules.loans.schemas import (
    LoanApplicationRequest, LoanApprovalRequest, LoanRejectionRequest,
    LoanRepaymentRequest, LoanEarlyPayoffRequest,
    LoanEligibilityRequest, LoanEligibilityResponse,
    LoanCalculatorRequest, LoanCalculatorResponse,
    LoanPaymentScheduleItem, LoanSummary
)
from app.modules.accounts.models import Account


class LoanService:
    """Comprehensive loan service with full banking features"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _generate_reference(self) -> str:
        """Generate unique loan reference number"""
        return f"LN-{uuid.uuid4().hex[:10].upper()}"
    
    def _calculate_monthly_payment(
        self,
        principal: Decimal,
        annual_rate: Decimal,
        term_months: int
    ) -> Decimal:
        """Calculate monthly payment using amortization formula"""
        if annual_rate == 0:
            return (principal / term_months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        monthly_rate = annual_rate / Decimal("100") / Decimal("12")
        
        # Formula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
        numerator = monthly_rate * ((1 + monthly_rate) ** term_months)
        denominator = ((1 + monthly_rate) ** term_months) - 1
        
        payment = principal * (numerator / denominator)
        return payment.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _generate_amortization_schedule(
        self,
        principal: Decimal,
        annual_rate: Decimal,
        term_months: int,
        start_date: date,
        frequency: RepaymentFrequency = RepaymentFrequency.MONTHLY
    ) -> List[dict]:
        """Generate full amortization schedule"""
        schedule = []
        monthly_payment = self._calculate_monthly_payment(principal, annual_rate, term_months)
        balance = principal
        monthly_rate = annual_rate / Decimal("100") / Decimal("12")
        
        # Determine date increment
        if frequency == RepaymentFrequency.WEEKLY:
            delta = timedelta(weeks=1)
        elif frequency == RepaymentFrequency.BI_WEEKLY:
            delta = timedelta(weeks=2)
        elif frequency == RepaymentFrequency.QUARTERLY:
            delta = relativedelta(months=3)
        else:  # Monthly
            delta = relativedelta(months=1)
        
        current_date = start_date
        
        for i in range(1, term_months + 1):
            interest = (balance * monthly_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            if i == term_months:
                # Final payment - clear remaining balance
                principal_payment = balance
                payment = principal_payment + interest
            else:
                principal_payment = monthly_payment - interest
            
            balance -= principal_payment
            
            schedule.append({
                "payment_number": i,
                "due_date": current_date,
                "scheduled_amount": monthly_payment if i < term_months else payment,
                "principal_component": principal_payment,
                "interest_component": interest,
                "balance_after": max(balance, Decimal("0.00")),
                "status": PaymentStatus.SCHEDULED
            })
            
            if isinstance(delta, relativedelta):
                current_date = current_date + delta
            else:
                current_date = current_date + delta
        
        return schedule
    
    async def _get_account(self, account_id: int) -> Optional[Account]:
        """Get account by ID"""
        result = await self.db.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()
    
    # ============================================================
    # Loan Products
    # ============================================================
    
    async def get_loan_products(self, active_only: bool = True) -> List[LoanProduct]:
        """Get all loan products"""
        query = select(LoanProduct)
        if active_only:
            query = query.where(LoanProduct.is_active == True)
        query = query.order_by(LoanProduct.loan_type)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_loan_product(self, product_id: int) -> Optional[LoanProduct]:
        """Get specific loan product"""
        result = await self.db.execute(
            select(LoanProduct).where(LoanProduct.id == product_id)
        )
        return result.scalar_one_or_none()
    
    async def create_loan_product(self, data: dict) -> LoanProduct:
        """Create a new loan product (admin)"""
        product = LoanProduct(**data)
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product
    
    # ============================================================
    # Loan Application
    # ============================================================
    
    async def apply_for_loan(
        self,
        user_id: int,
        request: LoanApplicationRequest
    ) -> Loan:
        """Create a new loan application"""
        
        # Get product
        product = await self.get_loan_product(request.product_id)
        if not product:
            raise ValueError("Loan product not found")
        
        if not product.is_active:
            raise ValueError("This loan product is not available")
        
        # Validate amount
        if request.requested_amount < product.min_amount:
            raise ValueError(f"Minimum loan amount is {product.min_amount}")
        if request.requested_amount > product.max_amount:
            raise ValueError(f"Maximum loan amount is {product.max_amount}")
        
        # Validate term
        if request.term_months < product.min_term_months:
            raise ValueError(f"Minimum term is {product.min_term_months} months")
        if request.term_months > product.max_term_months:
            raise ValueError(f"Maximum term is {product.max_term_months} months")
        
        # Verify account ownership
        account = await self._get_account(request.account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Invalid disbursement account")
        
        # Check collateral if required
        if product.requires_collateral and not request.collateral_type:
            raise ValueError("This loan requires collateral")
        
        # Calculate processing fee
        processing_fee = product.processing_fee_flat + (
            request.requested_amount * product.processing_fee_percentage
        )
        
        # Create loan
        loan = Loan(
            reference_number=self._generate_reference(),
            user_id=user_id,
            account_id=request.account_id,
            product_id=product.id,
            loan_type=product.loan_type,
            purpose=request.purpose,
            requested_amount=request.requested_amount,
            currency="USD",
            interest_rate=product.default_interest_rate,
            term_months=request.term_months,
            repayment_frequency=product.repayment_frequency,
            processing_fee=processing_fee,
            status=LoanStatus.DRAFT,
            # Employment info
            employer_name=request.employer_name,
            monthly_income=request.monthly_income,
            employment_duration_months=request.employment_duration_months,
            # Collateral
            collateral_type=request.collateral_type,
            collateral_description=request.collateral_description,
            collateral_value=request.collateral_value
        )
        
        self.db.add(loan)
        await self.db.commit()
        await self.db.refresh(loan)
        
        return loan
    
    async def submit_loan_application(self, loan_id: int, user_id: int) -> Loan:
        """Submit a draft loan for review"""
        loan = await self.get_user_loan(loan_id, user_id)
        
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.status != LoanStatus.DRAFT:
            raise ValueError("Only draft loans can be submitted")
        
        loan.status = LoanStatus.SUBMITTED
        loan.submitted_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(loan)
        
        return loan
    
    # ============================================================
    # Loan Approval (Admin)
    # ============================================================
    
    async def approve_loan(
        self,
        request: LoanApprovalRequest,
        reviewer_id: int
    ) -> Loan:
        """Approve a loan application"""
        result = await self.db.execute(
            select(Loan).where(Loan.id == request.loan_id)
        )
        loan = result.scalar_one_or_none()
        
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.status not in [LoanStatus.SUBMITTED, LoanStatus.UNDER_REVIEW]:
            raise ValueError("Loan is not pending approval")
        
        # Calculate loan details
        monthly_payment = self._calculate_monthly_payment(
            request.approved_amount,
            request.interest_rate,
            loan.term_months
        )
        total_repayment = monthly_payment * loan.term_months
        total_interest = total_repayment - request.approved_amount
        
        # Update loan
        loan.status = LoanStatus.APPROVED
        loan.approved_amount = request.approved_amount
        loan.interest_rate = request.interest_rate
        loan.monthly_payment = monthly_payment
        loan.total_repayment = total_repayment
        loan.total_interest = total_interest
        loan.outstanding_balance = request.approved_amount
        loan.payments_remaining = loan.term_months
        loan.approval_notes = request.approval_notes
        loan.reviewed_by = reviewer_id
        loan.reviewed_at = datetime.utcnow()
        loan.approved_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(loan)
        
        return loan
    
    async def reject_loan(
        self,
        request: LoanRejectionRequest,
        reviewer_id: int
    ) -> Loan:
        """Reject a loan application"""
        result = await self.db.execute(
            select(Loan).where(Loan.id == request.loan_id)
        )
        loan = result.scalar_one_or_none()
        
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.status not in [LoanStatus.SUBMITTED, LoanStatus.UNDER_REVIEW]:
            raise ValueError("Loan is not pending review")
        
        loan.status = LoanStatus.REJECTED
        loan.rejection_reason = request.rejection_reason
        loan.reviewed_by = reviewer_id
        loan.reviewed_at = datetime.utcnow()
        loan.rejected_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(loan)
        
        return loan
    
    async def disburse_loan(self, loan_id: int, admin_id: int) -> Loan:
        """Disburse an approved loan"""
        result = await self.db.execute(
            select(Loan).where(Loan.id == loan_id)
        )
        loan = result.scalar_one_or_none()
        
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.status != LoanStatus.APPROVED:
            raise ValueError("Loan must be approved before disbursement")
        
        # Get disbursement account
        account = await self._get_account(loan.account_id)
        if not account:
            raise ValueError("Disbursement account not found")
        
        # Credit account (minus processing fee)
        net_amount = loan.approved_amount - loan.processing_fee
        account.current_balance += net_amount
        account.available_balance += net_amount
        
        # Calculate dates
        first_payment_date = date.today() + relativedelta(months=1)
        maturity_date = first_payment_date + relativedelta(months=loan.term_months - 1)
        
        # Update loan
        loan.status = LoanStatus.ACTIVE
        loan.disbursed_amount = loan.approved_amount
        loan.disbursed_at = datetime.utcnow()
        loan.first_payment_date = first_payment_date
        loan.maturity_date = maturity_date
        loan.next_payment_date = first_payment_date
        
        # Generate payment schedule
        schedule = self._generate_amortization_schedule(
            loan.approved_amount,
            loan.interest_rate,
            loan.term_months,
            first_payment_date,
            loan.repayment_frequency
        )
        
        for payment_data in schedule:
            payment = LoanPayment(
                loan_id=loan.id,
                payment_number=payment_data["payment_number"],
                due_date=payment_data["due_date"],
                scheduled_amount=payment_data["scheduled_amount"],
                principal_component=payment_data["principal_component"],
                interest_component=payment_data["interest_component"],
                balance_after=payment_data["balance_after"],
                status=PaymentStatus.SCHEDULED
            )
            self.db.add(payment)
        
        await self.db.commit()
        await self.db.refresh(loan)
        
        return loan
    
    # ============================================================
    # Loan Repayment
    # ============================================================
    
    async def make_payment(
        self,
        request: LoanRepaymentRequest,
        user_id: int
    ) -> dict:
        """Make a loan payment"""
        
        # Get loan
        loan = await self.get_user_loan(request.loan_id, user_id)
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
            raise ValueError("Loan is not active")
        
        # Get source account
        source_account = await self._get_account(request.source_account_id)
        if not source_account or source_account.user_id != user_id:
            raise ValueError("Invalid source account")
        
        if source_account.available_balance < request.amount:
            raise ValueError("Insufficient funds")
        
        # Get next due payment
        result = await self.db.execute(
            select(LoanPayment).where(
                and_(
                    LoanPayment.loan_id == loan.id,
                    LoanPayment.status.in_([PaymentStatus.SCHEDULED, PaymentStatus.OVERDUE, PaymentStatus.PARTIAL])
                )
            ).order_by(LoanPayment.payment_number)
        )
        due_payments = list(result.scalars().all())
        
        if not due_payments:
            raise ValueError("No payments due")
        
        # Apply payment
        amount_remaining = request.amount
        payments_updated = []
        
        for payment in due_payments:
            if amount_remaining <= 0:
                break
            
            amount_due = payment.scheduled_amount - payment.paid_amount
            
            if amount_remaining >= amount_due:
                # Full payment
                payment.paid_amount = payment.scheduled_amount
                payment.paid_principal = payment.principal_component
                payment.paid_interest = payment.interest_component
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.utcnow()
                amount_remaining -= amount_due
                
                loan.payments_made += 1
                loan.payments_remaining -= 1
            else:
                # Partial payment
                payment.paid_amount += amount_remaining
                ratio = amount_remaining / payment.scheduled_amount
                payment.paid_principal += payment.principal_component * ratio
                payment.paid_interest += payment.interest_component * ratio
                payment.status = PaymentStatus.PARTIAL
                amount_remaining = Decimal("0")
            
            payments_updated.append(payment)
        
        # Update loan balances
        total_paid = request.amount - amount_remaining
        loan.total_paid += total_paid
        loan.principal_paid += sum(p.paid_principal for p in payments_updated) - sum(
            p.paid_principal for p in payments_updated if p.status == PaymentStatus.PARTIAL
        )
        loan.interest_paid += sum(p.paid_interest for p in payments_updated) - sum(
            p.paid_interest for p in payments_updated if p.status == PaymentStatus.PARTIAL
        )
        loan.outstanding_balance = loan.approved_amount - loan.principal_paid
        
        # Debit source account
        source_account.current_balance -= total_paid
        source_account.available_balance -= total_paid
        
        # Update next payment date
        next_payment = await self.db.execute(
            select(LoanPayment).where(
                and_(
                    LoanPayment.loan_id == loan.id,
                    LoanPayment.status == PaymentStatus.SCHEDULED
                )
            ).order_by(LoanPayment.payment_number).limit(1)
        )
        next_due = next_payment.scalar_one_or_none()
        loan.next_payment_date = next_due.due_date if next_due else None
        
        # Check if loan is paid off
        if loan.payments_remaining == 0:
            loan.status = LoanStatus.PAID_OFF
            loan.paid_off_at = datetime.utcnow()
            loan.outstanding_balance = Decimal("0")
        elif loan.status == LoanStatus.OVERDUE:
            loan.status = LoanStatus.ACTIVE
        
        await self.db.commit()
        
        return {
            "payment_id": payments_updated[0].id if payments_updated else None,
            "loan_id": loan.id,
            "amount_paid": total_paid,
            "new_balance": loan.outstanding_balance,
            "loan_status": loan.status,
            "payments_remaining": loan.payments_remaining
        }
    
    async def payoff_loan(
        self,
        request: LoanEarlyPayoffRequest,
        user_id: int
    ) -> Loan:
        """Pay off entire loan early"""
        loan = await self.get_user_loan(request.loan_id, user_id)
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
            raise ValueError("Loan is not active")
        
        payoff_amount = loan.outstanding_balance + loan.late_fees_accrued
        
        # Get source account
        source_account = await self._get_account(request.source_account_id)
        if not source_account or source_account.user_id != user_id:
            raise ValueError("Invalid source account")
        
        if source_account.available_balance < payoff_amount:
            raise ValueError(f"Insufficient funds. Payoff amount is {payoff_amount}")
        
        # Debit account
        source_account.current_balance -= payoff_amount
        source_account.available_balance -= payoff_amount
        
        # Update all remaining payments to paid
        await self.db.execute(
            update(LoanPayment)
            .where(
                and_(
                    LoanPayment.loan_id == loan.id,
                    LoanPayment.status.in_([PaymentStatus.SCHEDULED, PaymentStatus.OVERDUE, PaymentStatus.PARTIAL])
                )
            )
            .values(status=PaymentStatus.PAID, paid_at=datetime.utcnow())
        )
        
        # Update loan
        loan.total_paid += payoff_amount
        loan.principal_paid = loan.approved_amount
        loan.outstanding_balance = Decimal("0")
        loan.status = LoanStatus.PAID_OFF
        loan.paid_off_at = datetime.utcnow()
        loan.payments_remaining = 0
        loan.next_payment_date = None
        
        await self.db.commit()
        await self.db.refresh(loan)
        
        return loan
    
    # ============================================================
    # Loan Queries
    # ============================================================
    
    async def get_user_loan(self, loan_id: int, user_id: int) -> Optional[Loan]:
        """Get a specific loan for a user"""
        result = await self.db.execute(
            select(Loan).where(
                and_(
                    Loan.id == loan_id,
                    Loan.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_loans(
        self,
        user_id: int,
        status: Optional[LoanStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Loan], int]:
        """Get all loans for a user"""
        query = select(Loan).where(Loan.user_id == user_id)
        
        if status:
            query = query.where(Loan.status == status)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(Loan.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        loans = list(result.scalars().all())
        
        return loans, total
    
    async def get_loan_with_schedule(self, loan_id: int, user_id: int) -> Optional[dict]:
        """Get loan with full payment schedule"""
        loan = await self.get_user_loan(loan_id, user_id)
        if not loan:
            return None
        
        # Get payment schedule
        result = await self.db.execute(
            select(LoanPayment)
            .where(LoanPayment.loan_id == loan_id)
            .order_by(LoanPayment.payment_number)
        )
        payments = list(result.scalars().all())
        
        return {
            "loan": loan,
            "payment_schedule": payments
        }
    
    async def get_loan_summary(self, user_id: int) -> LoanSummary:
        """Get loan summary for dashboard"""
        result = await self.db.execute(
            select(Loan).where(Loan.user_id == user_id)
        )
        loans = list(result.scalars().all())
        
        active_statuses = [LoanStatus.ACTIVE, LoanStatus.OVERDUE, LoanStatus.DISBURSED]
        
        active_loans = [l for l in loans if l.status in active_statuses]
        total_borrowed = sum(l.disbursed_amount or Decimal("0") for l in loans if l.disbursed_amount)
        total_outstanding = sum(l.outstanding_balance or Decimal("0") for l in active_loans)
        total_paid = sum(l.total_paid or Decimal("0") for l in loans)
        overdue_amount = sum(l.outstanding_balance or Decimal("0") for l in loans if l.status == LoanStatus.OVERDUE)
        
        # Next payment
        next_payment = None
        next_date = None
        for loan in active_loans:
            if loan.next_payment_date and loan.monthly_payment:
                if not next_date or loan.next_payment_date < next_date:
                    next_date = loan.next_payment_date
                    next_payment = loan.monthly_payment
        
        # Status breakdown
        status_counts = {}
        for loan in loans:
            status_counts[loan.status.value] = status_counts.get(loan.status.value, 0) + 1
        
        return LoanSummary(
            total_loans=len(loans),
            active_loans=len(active_loans),
            total_borrowed=total_borrowed,
            total_outstanding=total_outstanding,
            total_paid=total_paid,
            next_payment_amount=next_payment,
            next_payment_date=next_date,
            overdue_amount=overdue_amount,
            loans_by_status=status_counts
        )
    
    # ============================================================
    # Loan Calculator / Eligibility
    # ============================================================
    
    async def check_eligibility(
        self,
        user_id: int,
        request: LoanEligibilityRequest
    ) -> LoanEligibilityResponse:
        """Check loan eligibility"""
        product = await self.get_loan_product(request.product_id)
        if not product:
            return LoanEligibilityResponse(
                eligible=False,
                max_eligible_amount=Decimal("0"),
                recommended_term_months=0,
                estimated_interest_rate=Decimal("0"),
                estimated_monthly_payment=Decimal("0"),
                estimated_total_repayment=Decimal("0"),
                reasons=["Loan product not found"]
            )
        
        reasons = []
        eligible = True
        
        # Check amount
        if request.requested_amount < product.min_amount:
            reasons.append(f"Amount below minimum ({product.min_amount})")
            eligible = False
        if request.requested_amount > product.max_amount:
            reasons.append(f"Amount exceeds maximum ({product.max_amount})")
            eligible = False
        
        # Check term
        if request.term_months < product.min_term_months:
            reasons.append(f"Term below minimum ({product.min_term_months} months)")
            eligible = False
        if request.term_months > product.max_term_months:
            reasons.append(f"Term exceeds maximum ({product.max_term_months} months)")
            eligible = False
        
        # Check income (if provided)
        max_eligible = product.max_amount
        if request.monthly_income and product.min_income:
            if request.monthly_income < product.min_income:
                reasons.append(f"Income below minimum requirement ({product.min_income})")
                eligible = False
            else:
                # Max loan typically 40% of monthly income * term
                max_affordable = request.monthly_income * Decimal("0.4") * request.term_months
                max_eligible = min(max_eligible, max_affordable)
        
        # Calculate estimates
        monthly_payment = self._calculate_monthly_payment(
            request.requested_amount,
            product.default_interest_rate,
            request.term_months
        )
        total_repayment = monthly_payment * request.term_months
        
        return LoanEligibilityResponse(
            eligible=eligible,
            max_eligible_amount=max_eligible,
            recommended_term_months=request.term_months,
            estimated_interest_rate=product.default_interest_rate,
            estimated_monthly_payment=monthly_payment,
            estimated_total_repayment=total_repayment,
            reasons=reasons
        )
    
    def calculate_loan(self, request: LoanCalculatorRequest) -> LoanCalculatorResponse:
        """Calculate loan details and amortization"""
        monthly_payment = self._calculate_monthly_payment(
            request.principal,
            request.interest_rate,
            request.term_months
        )
        total_repayment = monthly_payment * request.term_months
        total_interest = total_repayment - request.principal
        
        schedule = self._generate_amortization_schedule(
            request.principal,
            request.interest_rate,
            request.term_months,
            date.today() + relativedelta(months=1),
            request.repayment_frequency
        )
        
        schedule_items = [
            LoanPaymentScheduleItem(
                payment_number=s["payment_number"],
                due_date=s["due_date"],
                scheduled_amount=s["scheduled_amount"],
                principal_component=s["principal_component"],
                interest_component=s["interest_component"],
                balance_after=s["balance_after"],
                status=s["status"]
            )
            for s in schedule
        ]
        
        return LoanCalculatorResponse(
            principal=request.principal,
            interest_rate=request.interest_rate,
            term_months=request.term_months,
            monthly_payment=monthly_payment,
            total_interest=total_interest,
            total_repayment=total_repayment,
            amortization_schedule=schedule_items
        )
