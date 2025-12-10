from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status
from datetime import datetime, date, timedelta
from typing import List, Optional
from decimal import Decimal
import random
import hashlib
from cryptography.fernet import Fernet

from app.core.security import get_password_hash
from app.core.config import settings
from app.modules.cards.models import VirtualCard, CardType, CardStatus, CardTier, FraudAlertLevel, CreatedBy
from app.modules.cards import schemas
from app.modules.accounts.models import Account
from app.modules.users.models import User


class CardService:
    """Service layer for virtual card management"""
    
    # Simple encryption key (in production, use proper key management)
    ENCRYPTION_KEY = Fernet.generate_key()
    cipher = Fernet(ENCRYPTION_KEY)
    
    @staticmethod
    def luhn_checksum(card_number: str) -> int:
        """Calculate Luhn checksum for card number validation"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10
    
    @staticmethod
    def generate_card_number(card_type: CardType) -> str:
        """Generate valid card number using Luhn algorithm"""
        # Visa starts with 4, Mastercard starts with 5
        if card_type == CardType.VISA:
            prefix = "4"
        else:  # Mastercard
            prefix = "5"
        
        # Generate 15 random digits
        middle_digits = ''.join([str(random.randint(0, 9)) for _ in range(14)])
        partial_number = prefix + middle_digits
        
        # Calculate check digit
        checksum = CardService.luhn_checksum(partial_number + "0")
        check_digit = (10 - checksum) % 10
        
        return partial_number + str(check_digit)
    
    @staticmethod
    def generate_cvv() -> str:
        """Generate 3-digit CVV"""
        return ''.join([str(random.randint(0, 9)) for _ in range(3)])
    
    @staticmethod
    def encrypt_card_number(card_number: str) -> str:
        """Encrypt card number"""
        return CardService.cipher.encrypt(card_number.encode()).decode()
    
    @staticmethod
    def decrypt_card_number(encrypted: str) -> str:
        """Decrypt card number"""
        return CardService.cipher.decrypt(encrypted.encode()).decode()
    
    @staticmethod
    def hash_card_number(card_number: str) -> str:
        """Hash card number for verification"""
        return hashlib.sha256(card_number.encode()).hexdigest()
    
    @staticmethod
    def mask_card_number(card_number: str) -> str:
        """Mask card number showing only last 4 digits"""
        return f"************{card_number[-4:]}"
    
    @staticmethod
    async def create_virtual_card(
        db: AsyncSession,
        user_id: int,
        card_data: schemas.VirtualCardCreateRequest
    ) -> tuple[VirtualCard, str, str]:
        """Create a new virtual card - returns (card, full_card_number, cvv)"""
        
        # Verify account exists and belongs to user
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.id == card_data.account_id,
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
        
        # Get user for card holder name
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate card details
        card_number = CardService.generate_card_number(card_data.card_type)
        cvv = CardService.generate_cvv()
        
        # Calculate expiry date (3 years from now)
        expiry_date = date.today() + timedelta(days=3*365)
        
        # Create card
        card = VirtualCard(
            user_id=user_id,
            account_id=card_data.account_id,
            card_number_encrypted=CardService.encrypt_card_number(card_number),
            card_hash=CardService.hash_card_number(card_number),
            expiry_month=expiry_date.month,
            expiry_year=expiry_date.year,
            cvv_hash=get_password_hash(cvv),
            card_type=card_data.card_type,
            card_network=card_data.card_type,
            card_holder_name=f"{user.first_name} {user.last_name}".upper(),
            card_tier=card_data.card_tier,
            card_expiry_date=expiry_date,
            daily_spend_limit=card_data.daily_spend_limit or Decimal("5000.00"),
            monthly_spend_limit=card_data.monthly_spend_limit or Decimal("15000.00"),
            created_by=CreatedBy.USER
        )
        
        db.add(card)
        await db.commit()
        await db.refresh(card)
        
        # Return card with full details (only shown once)
        return card, card_number, cvv
    
    @staticmethod
    async def get_user_cards(db: AsyncSession, user_id: int) -> List[VirtualCard]:
        """Get all cards for a user"""
        result = await db.execute(
            select(VirtualCard).where(
                and_(
                    VirtualCard.user_id == user_id,
                    VirtualCard.card_status != CardStatus.CANCELLED
                )
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_card(db: AsyncSession, card_id: int, user_id: int) -> VirtualCard:
        """Get specific card"""
        result = await db.execute(
            select(VirtualCard).where(
                and_(
                    VirtualCard.id == card_id,
                    VirtualCard.user_id == user_id
                )
            )
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found"
            )
        
        return card
    
    @staticmethod
    async def block_unblock_card(
        db: AsyncSession,
        card_id: int,
        user_id: int,
        block_data: schemas.CardBlockRequest
    ) -> VirtualCard:
        """Block or unblock a card"""
        card = await CardService.get_card(db, card_id, user_id)
        
        if block_data.block:
            card.card_status = CardStatus.BLOCKED
            card.temp_lock_reason = block_data.reason
        else:
            card.card_status = CardStatus.ACTIVE
            card.temp_lock_reason = None
        
        await db.commit()
        await db.refresh(card)
        
        return card
    
    @staticmethod
    async def update_card_limits(
        db: AsyncSession,
        card_id: int,
        user_id: int,
        limits: schemas.CardLimitsUpdate
    ) -> VirtualCard:
        """Update card spending limits"""
        card = await CardService.get_card(db, card_id, user_id)
        
        update_data = limits.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)
        
        await db.commit()
        await db.refresh(card)
        
        return card
    
    @staticmethod
    async def update_card_controls(
        db: AsyncSession,
        card_id: int,
        user_id: int,
        controls: schemas.CardControlsUpdate
    ) -> VirtualCard:
        """Update card controls"""
        card = await CardService.get_card(db, card_id, user_id)
        
        update_data = controls.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)
        
        await db.commit()
        await db.refresh(card)
        
        return card
    
    @staticmethod
    async def cancel_card(
        db: AsyncSession,
        card_id: int,
        user_id: int,
        cancellation_data: schemas.CardCancellationRequest
    ) -> bool:
        """Cancel a virtual card"""
        card = await CardService.get_card(db, card_id, user_id)
        
        card.card_status = CardStatus.CANCELLED
        card.cancellation_date = datetime.utcnow()
        card.cancellation_reason = cancellation_data.reason
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def set_card_pin(
        db: AsyncSession,
        card_id: int,
        user_id: int,
        pin_data: schemas.CardPINSetRequest
    ) -> bool:
        """Set or change card PIN"""
        card = await CardService.get_card(db, card_id, user_id)
        
        # Hash and store PIN
        card.pin_hash = get_password_hash(pin_data.pin)
        card.pin_attempts = 0
        card.pin_locked_until = None
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def activate_card(
        db: AsyncSession,
        card_id: int,
        user_id: int
    ) -> VirtualCard:
        """Activate a card"""
        card = await CardService.get_card(db, card_id, user_id)
        
        if card.card_status == CardStatus.INACTIVE:
            card.card_status = CardStatus.ACTIVE
            card.activation_date = datetime.utcnow()
            await db.commit()
            await db.refresh(card)
        
        return card
    
    @staticmethod
    async def temp_lock_card(
        db: AsyncSession,
        card_id: int,
        user_id: int,
        lock_data: schemas.CardTempLockRequest
    ) -> VirtualCard:
        """Temporarily lock a card"""
        card = await CardService.get_card(db, card_id, user_id)
        
        card.card_status = CardStatus.BLOCKED
        card.temp_lock_reason = lock_data.reason
        # Card will auto-unlock after specified hours (would need background job)
        
        await db.commit()
        await db.refresh(card)
        
        return card
    
    @staticmethod
    async def get_card_balance(
        db: AsyncSession,
        card_id: int,
        user_id: int
    ) -> schemas.CardBalanceResponse:
        """Get card available balance"""
        card = await CardService.get_card(db, card_id, user_id)
        
        # Get account balance
        result = await db.execute(
            select(Account).where(Account.id == card.account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated account not found"
            )
        
        return schemas.CardBalanceResponse(
            card_id=card.id,
            account_id=account.id,
            available_balance=account.available_balance,
            daily_remaining=card.daily_spend_limit,  # Would calculate actual remaining
            monthly_remaining=card.monthly_spend_limit  # Would calculate actual remaining
        )
