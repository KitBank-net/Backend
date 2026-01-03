from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import uuid

# Optional QR code support
try:
    import qrcode
    import io
    import base64
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

from app.modules.transactions.models import (
    Transaction, TransactionFee, QRCode,
    TransactionType, TransactionStatus, TransactionChannel, Currency
)
from app.modules.transactions.schemas import (
    InternalTransferRequest, P2PTransferRequest, QRCodeGenerateRequest,
    QRPaymentRequest, BillPaymentRequest, MobileMoneyTransferRequest,
    InternationalTransferRequest, TransactionHistoryFilter,
    FeeCalculationRequest, FeeCalculationResponse, ExchangeRateResponse
)
from app.modules.accounts.models import Account


class TransactionService:
    """Comprehensive transaction service with all payment types"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _generate_reference(self) -> str:
        """Generate unique transaction reference"""
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"
    
    async def _get_account(self, account_id: int) -> Optional[Account]:
        """Get account by ID"""
        result = await self.db.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_account_by_number(self, account_number: str) -> Optional[Account]:
        """Get account by account number"""
        result = await self.db.execute(
            select(Account).where(Account.account_number == account_number)
        )
        return result.scalar_one_or_none()
    
    async def _calculate_fee(
        self, 
        transaction_type: TransactionType, 
        amount: Decimal,
        currency: Currency
    ) -> Tuple[Decimal, dict]:
        """Calculate transaction fee based on fee configuration"""
        result = await self.db.execute(
            select(TransactionFee).where(
                and_(
                    TransactionFee.transaction_type == transaction_type,
                    TransactionFee.currency == currency,
                    TransactionFee.is_active == True
                )
            )
        )
        fee_config = result.scalar_one_or_none()
        
        if not fee_config:
            return Decimal("0.00"), {"flat_fee": 0, "percentage_fee": 0}
        
        # Calculate fee
        flat_fee = fee_config.flat_fee or Decimal("0.00")
        percentage_fee = amount * (fee_config.percentage_fee or Decimal("0.00"))
        total_fee = flat_fee + percentage_fee
        
        # Apply min/max
        if fee_config.min_fee and total_fee < fee_config.min_fee:
            total_fee = fee_config.min_fee
        if fee_config.max_fee and total_fee > fee_config.max_fee:
            total_fee = fee_config.max_fee
        
        breakdown = {
            "flat_fee": float(flat_fee),
            "percentage_fee": float(percentage_fee),
            "percentage_rate": float(fee_config.percentage_fee or 0),
            "total_fee": float(total_fee)
        }
        
        return total_fee, breakdown
    
    async def _validate_account_balance(
        self, 
        account: Account, 
        amount: Decimal
    ) -> bool:
        """Check if account has sufficient balance"""
        return account.available_balance >= amount
    
    async def _update_account_balance(
        self, 
        account: Account, 
        amount: Decimal, 
        is_credit: bool
    ) -> Tuple[Decimal, Decimal]:
        """Update account balance and return before/after"""
        balance_before = account.current_balance
        
        if is_credit:
            account.current_balance += amount
            account.available_balance += amount
        else:
            account.current_balance -= amount
            account.available_balance -= amount
        
        balance_after = account.current_balance
        return balance_before, balance_after
    
    # ============================================================
    # Internal Transfer
    # ============================================================
    
    async def create_internal_transfer(
        self,
        request: InternalTransferRequest,
        user_id: int,
        channel: TransactionChannel = TransactionChannel.API,
        ip_address: Optional[str] = None
    ) -> Transaction:
        """Transfer between own accounts"""
        
        # Get accounts
        source_account = await self._get_account(request.source_account_id)
        dest_account = await self._get_account(request.destination_account_id)
        
        if not source_account:
            raise ValueError("Source account not found")
        if not dest_account:
            raise ValueError("Destination account not found")
        
        # Validate ownership
        if source_account.user_id != user_id or dest_account.user_id != user_id:
            raise ValueError("Can only transfer between your own accounts")
        
        # Validate balance
        if not await self._validate_account_balance(source_account, request.amount):
            raise ValueError("Insufficient funds")
        
        # Calculate fee (usually free for internal transfers)
        fee_amount, _ = await self._calculate_fee(
            TransactionType.TRANSFER, request.amount, request.currency
        )
        total_amount = request.amount + fee_amount
        
        # Update balances
        source_before, source_after = await self._update_account_balance(
            source_account, total_amount, is_credit=False
        )
        dest_before, dest_after = await self._update_account_balance(
            dest_account, request.amount, is_credit=True
        )
        
        # Create transaction
        transaction = Transaction(
            reference_code=self._generate_reference(),
            source_account_id=source_account.id,
            source_account_number=source_account.account_number,
            destination_account_id=dest_account.id,
            destination_account_number=dest_account.account_number,
            amount=request.amount,
            currency=request.currency,
            fee_amount=fee_amount,
            total_amount=total_amount,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            channel=channel,
            description=request.description,
            narration=request.narration or f"Transfer to {dest_account.account_number}",
            source_balance_before=source_before,
            source_balance_after=source_after,
            destination_balance_before=dest_before,
            destination_balance_after=dest_after,
            ip_address=ip_address,
            completed_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    # ============================================================
    # P2P Transfer
    # ============================================================
    
    async def create_p2p_transfer(
        self,
        request: P2PTransferRequest,
        user_id: int,
        channel: TransactionChannel = TransactionChannel.API,
        ip_address: Optional[str] = None
    ) -> Transaction:
        """Peer-to-peer transfer to another user"""
        
        # Get source account
        source_account = await self._get_account(request.source_account_id)
        if not source_account:
            raise ValueError("Source account not found")
        if source_account.user_id != user_id:
            raise ValueError("Account does not belong to user")
        
        # Find destination account
        dest_account = None
        if request.recipient_account_number:
            dest_account = await self._get_account_by_number(request.recipient_account_number)
        # TODO: Add lookup by phone/email
        
        if not dest_account:
            raise ValueError("Recipient not found")
        
        if source_account.id == dest_account.id:
            raise ValueError("Cannot transfer to the same account")
        
        # Calculate fee
        fee_amount, _ = await self._calculate_fee(
            TransactionType.P2P, request.amount, request.currency
        )
        total_amount = request.amount + fee_amount
        
        # Validate balance
        if not await self._validate_account_balance(source_account, total_amount):
            raise ValueError("Insufficient funds")
        
        # Update balances
        source_before, source_after = await self._update_account_balance(
            source_account, total_amount, is_credit=False
        )
        dest_before, dest_after = await self._update_account_balance(
            dest_account, request.amount, is_credit=True
        )
        
        # Create transaction
        transaction = Transaction(
            reference_code=self._generate_reference(),
            source_account_id=source_account.id,
            source_account_number=source_account.account_number,
            destination_account_id=dest_account.id,
            destination_account_number=dest_account.account_number,
            amount=request.amount,
            currency=request.currency,
            fee_amount=fee_amount,
            total_amount=total_amount,
            transaction_type=TransactionType.P2P,
            status=TransactionStatus.COMPLETED,
            channel=channel,
            description=request.description,
            narration=request.narration or f"P2P to {dest_account.account_number[-4:]}",
            source_balance_before=source_before,
            source_balance_after=source_after,
            destination_balance_before=dest_before,
            destination_balance_after=dest_after,
            ip_address=ip_address,
            completed_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    # ============================================================
    # QR Code Payment
    # ============================================================
    
    async def generate_qr_code(
        self,
        request: QRCodeGenerateRequest,
        user_id: int
    ) -> QRCode:
        """Generate QR code for receiving payments"""
        
        account = await self._get_account(request.account_id)
        if not account:
            raise ValueError("Account not found")
        if account.user_id != user_id:
            raise ValueError("Account does not belong to user")
        
        # Generate QR data
        qr_data = {
            "type": "kitbank_payment",
            "account": account.account_number,
            "amount": str(request.amount) if request.amount else None,
            "currency": request.currency.value,
            "ref": uuid.uuid4().hex[:8]
        }
        qr_data_str = str(qr_data)
        
        # Generate QR image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Calculate expiry
        expires_at = None
        if request.expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
        
        # Save QR code
        qr_code = QRCode(
            account_id=account.id,
            user_id=user_id,
            qr_code_data=qr_data_str,
            qr_code_image_url=f"data:image/png;base64,{qr_image_base64}",
            amount=request.amount,
            currency=request.currency,
            expires_at=expires_at,
            is_active=True
        )
        
        self.db.add(qr_code)
        await self.db.commit()
        await self.db.refresh(qr_code)
        
        return qr_code
    
    async def process_qr_payment(
        self,
        request: QRPaymentRequest,
        user_id: int,
        channel: TransactionChannel = TransactionChannel.MOBILE_APP,
        ip_address: Optional[str] = None
    ) -> Transaction:
        """Process payment via QR code scan"""
        
        # Parse QR data and find recipient
        # In production, QR data would be properly encoded/encrypted
        result = await self.db.execute(
            select(QRCode).where(
                and_(
                    QRCode.qr_code_data == request.qr_code_data,
                    QRCode.is_active == True
                )
            )
        )
        qr_code = result.scalar_one_or_none()
        
        if not qr_code:
            raise ValueError("Invalid or expired QR code")
        
        if qr_code.expires_at and qr_code.expires_at < datetime.utcnow():
            raise ValueError("QR code has expired")
        
        # Get accounts
        source_account = await self._get_account(request.source_account_id)
        dest_account = await self._get_account(qr_code.account_id)
        
        if not source_account:
            raise ValueError("Source account not found")
        if source_account.user_id != user_id:
            raise ValueError("Account does not belong to user")
        
        # Use QR amount if specified, otherwise use request amount
        amount = qr_code.amount if qr_code.amount else request.amount
        
        # Calculate fee
        fee_amount, _ = await self._calculate_fee(
            TransactionType.QR_PAYMENT, amount, request.currency
        )
        total_amount = amount + fee_amount
        
        # Validate balance
        if not await self._validate_account_balance(source_account, total_amount):
            raise ValueError("Insufficient funds")
        
        # Update balances
        source_before, source_after = await self._update_account_balance(
            source_account, total_amount, is_credit=False
        )
        dest_before, dest_after = await self._update_account_balance(
            dest_account, amount, is_credit=True
        )
        
        # Update QR scan count
        qr_code.scan_count += 1
        qr_code.last_scanned_at = datetime.utcnow()
        
        # Create transaction
        transaction = Transaction(
            reference_code=self._generate_reference(),
            source_account_id=source_account.id,
            source_account_number=source_account.account_number,
            destination_account_id=dest_account.id,
            destination_account_number=dest_account.account_number,
            amount=amount,
            currency=request.currency,
            fee_amount=fee_amount,
            total_amount=total_amount,
            transaction_type=TransactionType.QR_PAYMENT,
            status=TransactionStatus.COMPLETED,
            channel=channel,
            description=request.description,
            narration=f"QR Payment",
            qr_code=request.qr_code_data,
            source_balance_before=source_before,
            source_balance_after=source_after,
            destination_balance_before=dest_before,
            destination_balance_after=dest_after,
            ip_address=ip_address,
            completed_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    # ============================================================
    # Bill Payment
    # ============================================================
    
    async def create_bill_payment(
        self,
        request: BillPaymentRequest,
        user_id: int,
        channel: TransactionChannel = TransactionChannel.API,
        ip_address: Optional[str] = None
    ) -> Transaction:
        """Pay a bill to a biller"""
        
        # Get source account
        source_account = await self._get_account(request.source_account_id)
        if not source_account:
            raise ValueError("Source account not found")
        if source_account.user_id != user_id:
            raise ValueError("Account does not belong to user")
        
        # TODO: Validate biller code against biller registry
        # TODO: Validate bill reference with biller API
        
        # Calculate fee
        fee_amount, _ = await self._calculate_fee(
            TransactionType.BILL_PAYMENT, request.amount, request.currency
        )
        total_amount = request.amount + fee_amount
        
        # Validate balance
        if not await self._validate_account_balance(source_account, total_amount):
            raise ValueError("Insufficient funds")
        
        # Update balance
        source_before, source_after = await self._update_account_balance(
            source_account, total_amount, is_credit=False
        )
        
        # Create transaction
        transaction = Transaction(
            reference_code=self._generate_reference(),
            source_account_id=source_account.id,
            source_account_number=source_account.account_number,
            amount=request.amount,
            currency=request.currency,
            fee_amount=fee_amount,
            total_amount=total_amount,
            transaction_type=TransactionType.BILL_PAYMENT,
            status=TransactionStatus.COMPLETED,
            channel=channel,
            description=request.description,
            narration=f"Bill Payment - {request.biller_code}",
            biller_code=request.biller_code,
            bill_reference=request.bill_reference,
            source_balance_before=source_before,
            source_balance_after=source_after,
            ip_address=ip_address,
            completed_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    # ============================================================
    # Mobile Money Transfer
    # ============================================================
    
    async def create_mobile_money_transfer(
        self,
        request: MobileMoneyTransferRequest,
        user_id: int,
        channel: TransactionChannel = TransactionChannel.API,
        ip_address: Optional[str] = None
    ) -> Transaction:
        """Transfer to a mobile money wallet"""
        
        # Get source account
        source_account = await self._get_account(request.source_account_id)
        if not source_account:
            raise ValueError("Source account not found")
        if source_account.user_id != user_id:
            raise ValueError("Account does not belong to user")
        
        # Calculate fee
        fee_amount, _ = await self._calculate_fee(
            TransactionType.MOBILE_MONEY, request.amount, request.currency
        )
        total_amount = request.amount + fee_amount
        
        # Validate balance
        if not await self._validate_account_balance(source_account, total_amount):
            raise ValueError("Insufficient funds")
        
        # Update balance
        source_before, source_after = await self._update_account_balance(
            source_account, total_amount, is_credit=False
        )
        
        # Create transaction (status PENDING - requires external processing)
        transaction = Transaction(
            reference_code=self._generate_reference(),
            source_account_id=source_account.id,
            source_account_number=source_account.account_number,
            amount=request.amount,
            currency=request.currency,
            fee_amount=fee_amount,
            total_amount=total_amount,
            transaction_type=TransactionType.MOBILE_MONEY,
            status=TransactionStatus.PROCESSING,  # Needs external API call
            channel=channel,
            description=request.description,
            narration=request.narration or f"Mobile Money to {request.mobile_number[-4:]}",
            mobile_money_provider=request.provider.value,
            mobile_number=request.mobile_number,
            beneficiary_name=request.recipient_name,
            beneficiary_phone=request.mobile_number,
            source_balance_before=source_before,
            source_balance_after=source_after,
            ip_address=ip_address,
            processed_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        # TODO: Call mobile money provider API (M-Pesa, MTN, etc.)
        # On success, update status to COMPLETED
        # For now, we'll simulate successful completion
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    # ============================================================
    # International Transfer
    # ============================================================
    
    async def create_international_transfer(
        self,
        request: InternationalTransferRequest,
        user_id: int,
        channel: TransactionChannel = TransactionChannel.API,
        ip_address: Optional[str] = None
    ) -> Transaction:
        """Create an international wire transfer"""
        
        # Get source account
        source_account = await self._get_account(request.source_account_id)
        if not source_account:
            raise ValueError("Source account not found")
        if source_account.user_id != user_id:
            raise ValueError("Account does not belong to user")
        
        # Calculate FX if destination currency differs
        exchange_rate = None
        original_amount = None
        original_currency = None
        
        if request.destination_currency and request.destination_currency != request.currency:
            fx_response = await self.get_exchange_rate(
                request.currency,
                request.destination_currency,
                request.amount
            )
            exchange_rate = fx_response.rate
            original_amount = request.amount
            original_currency = request.currency
        
        # Calculate fee (international transfers have higher fees)
        fee_amount, _ = await self._calculate_fee(
            TransactionType.INTERNATIONAL, request.amount, request.currency
        )
        total_amount = request.amount + fee_amount
        
        # Validate balance
        if not await self._validate_account_balance(source_account, total_amount):
            raise ValueError("Insufficient funds")
        
        # Update balance
        source_before, source_after = await self._update_account_balance(
            source_account, total_amount, is_credit=False
        )
        
        # Create transaction (PENDING - requires compliance review for large amounts)
        requires_approval = request.amount >= 10000  # Flag large transfers
        
        transaction = Transaction(
            reference_code=self._generate_reference(),
            source_account_id=source_account.id,
            source_account_number=source_account.account_number,
            destination_account_number=request.account_number,
            destination_bank_name=request.bank_name,
            amount=request.amount,
            currency=request.currency,
            original_amount=original_amount,
            original_currency=original_currency,
            exchange_rate=exchange_rate,
            fee_amount=fee_amount,
            total_amount=total_amount,
            transaction_type=TransactionType.INTERNATIONAL,
            status=TransactionStatus.PENDING if requires_approval else TransactionStatus.PROCESSING,
            channel=channel,
            description=request.description or request.purpose_description,
            narration=request.narration or f"Intl Transfer to {request.beneficiary_name}",
            beneficiary_name=request.beneficiary_name,
            swift_code=request.swift_code,
            iban=request.iban,
            routing_number=request.routing_number,
            purpose_code=request.purpose_code,
            source_balance_before=source_before,
            source_balance_after=source_after,
            ip_address=ip_address,
            requires_approval=requires_approval,
            processed_at=datetime.utcnow() if not requires_approval else None
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        # TODO: For non-approval required transfers, call SWIFT/correspondent bank API
        # For now, simulate processing for small transfers
        if not requires_approval:
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(transaction)
        
        return transaction
    
    # ============================================================
    # Transaction History
    # ============================================================
    
    async def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Get single transaction by ID"""
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()
    
    async def get_transaction_by_reference(self, reference: str) -> Optional[Transaction]:
        """Get transaction by reference code"""
        result = await self.db.execute(
            select(Transaction).where(Transaction.reference_code == reference)
        )
        return result.scalar_one_or_none()
    
    async def get_transactions(
        self,
        user_id: int,
        filters: Optional[TransactionHistoryFilter] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Transaction], int]:
        """Get transactions with filters and pagination"""
        
        # Base query - get user's accounts first
        accounts_result = await self.db.execute(
            select(Account.id).where(Account.user_id == user_id)
        )
        user_account_ids = [a for a in accounts_result.scalars().all()]
        
        if not user_account_ids:
            return [], 0
        
        # Build query
        query = select(Transaction).where(
            or_(
                Transaction.source_account_id.in_(user_account_ids),
                Transaction.destination_account_id.in_(user_account_ids)
            )
        )
        
        # Apply filters
        if filters:
            if filters.account_id:
                query = query.where(
                    or_(
                        Transaction.source_account_id == filters.account_id,
                        Transaction.destination_account_id == filters.account_id
                    )
                )
            if filters.transaction_type:
                query = query.where(Transaction.transaction_type == filters.transaction_type)
            if filters.status:
                query = query.where(Transaction.status == filters.status)
            if filters.currency:
                query = query.where(Transaction.currency == filters.currency)
            if filters.min_amount:
                query = query.where(Transaction.amount >= filters.min_amount)
            if filters.max_amount:
                query = query.where(Transaction.amount <= filters.max_amount)
            if filters.start_date:
                query = query.where(Transaction.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(Transaction.created_at <= filters.end_date)
            if filters.reference_code:
                query = query.where(Transaction.reference_code.ilike(f"%{filters.reference_code}%"))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(Transaction.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        transactions = result.scalars().all()
        
        return list(transactions), total
    
    # ============================================================
    # Fee Calculation
    # ============================================================
    
    async def calculate_fee(self, request: FeeCalculationRequest) -> FeeCalculationResponse:
        """Calculate fee for a transaction type"""
        fee_amount, breakdown = await self._calculate_fee(
            request.transaction_type, request.amount, request.currency
        )
        
        return FeeCalculationResponse(
            transaction_type=request.transaction_type,
            amount=request.amount,
            currency=request.currency,
            fee_amount=fee_amount,
            total_amount=request.amount + fee_amount,
            fee_breakdown=breakdown
        )
    
    # ============================================================
    # Exchange Rates (Placeholder)
    # ============================================================
    
    async def get_exchange_rate(
        self, 
        from_currency: Currency, 
        to_currency: Currency,
        amount: Decimal
    ) -> ExchangeRateResponse:
        """Get exchange rate for currency conversion"""
        # TODO: Integrate with real FX provider
        # Placeholder rates
        rates = {
            ("USD", "EUR"): Decimal("0.92"),
            ("USD", "GBP"): Decimal("0.79"),
            ("USD", "KES"): Decimal("153.50"),
            ("EUR", "USD"): Decimal("1.09"),
            ("GBP", "USD"): Decimal("1.27"),
        }
        
        rate_key = (from_currency.value, to_currency.value)
        rate = rates.get(rate_key, Decimal("1.0"))
        
        return ExchangeRateResponse(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            amount=amount,
            converted_amount=amount * rate,
            valid_until=datetime.utcnow() + timedelta(minutes=15)
        )
