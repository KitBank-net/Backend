from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_kyc_verified
from app.modules.users.models import User
from app.modules.cards import schemas, services
from app.core.security import mask_card_number

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


@router.post("/virtual", response_model=schemas.VirtualCardFullResponse, status_code=status.HTTP_201_CREATED)
async def create_virtual_card(
    card_data: schemas.VirtualCardCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_kyc_verified)
):
    """
    Generate a new virtual card.
    
    - Requires KYC verification
    - Card number generated using Luhn algorithm
    - Full card details shown only once
    - Supports Visa and Mastercard
    """
    card, card_number, cvv = await services.CardService.create_virtual_card(
        db, current_user.id, card_data
    )
    
    return schemas.VirtualCardFullResponse(
        id=card.id,
        account_id=card.account_id,
        card_number=card_number,
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        cvv=cvv,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit
    )


@router.get("", response_model=List[schemas.VirtualCardResponse])
async def list_cards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all user cards.
    
    - Card numbers are masked
    - Excludes cancelled cards
    """
    cards = await services.CardService.get_user_cards(db, current_user.id)
    
    response = []
    for card in cards:
        # Decrypt and mask card number
        card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
        
        response.append(schemas.VirtualCardResponse(
            id=card.id,
            account_id=card.account_id,
            card_number_masked=mask_card_number(card_number),
            expiry_month=card.expiry_month,
            expiry_year=card.expiry_year,
            card_holder_name=card.card_holder_name,
            card_type=card.card_type.value,
            card_status=card.card_status.value,
            card_tier=card.card_tier.value,
            daily_spend_limit=card.daily_spend_limit,
            monthly_spend_limit=card.monthly_spend_limit,
            transaction_limit=card.transaction_limit,
            atm_withdrawal_limit=card.atm_withdrawal_limit,
            international_use=card.international_use,
            online_purchases=card.online_purchases,
            contactless_payments=card.contactless_payments,
            card_issue_date=card.card_issue_date,
            card_expiry_date=card.card_expiry_date,
            created_at=card.created_at
        ))
    
    return response


@router.get("/{card_id}", response_model=schemas.VirtualCardResponse)
async def get_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get card details (masked).
    """
    card = await services.CardService.get_card(db, card_id, current_user.id)
    
    card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
    
    return schemas.VirtualCardResponse(
        id=card.id,
        account_id=card.account_id,
        card_number_masked=mask_card_number(card_number),
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_status=card.card_status.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit,
        transaction_limit=card.transaction_limit,
        atm_withdrawal_limit=card.atm_withdrawal_limit,
        international_use=card.international_use,
        online_purchases=card.online_purchases,
        contactless_payments=card.contactless_payments,
        card_issue_date=card.card_issue_date,
        card_expiry_date=card.card_expiry_date,
        created_at=card.created_at
    )


@router.put("/{card_id}/block", response_model=schemas.VirtualCardResponse)
async def block_unblock_card(
    card_id: int,
    block_data: schemas.CardBlockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Block or unblock card.
    
    - Instantly blocks card for security
    - Can be unblocked by user
    """
    card = await services.CardService.block_unblock_card(db, card_id, current_user.id, block_data)
    
    card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
    
    return schemas.VirtualCardResponse(
        id=card.id,
        account_id=card.account_id,
        card_number_masked=mask_card_number(card_number),
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_status=card.card_status.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit,
        transaction_limit=card.transaction_limit,
        atm_withdrawal_limit=card.atm_withdrawal_limit,
        international_use=card.international_use,
        online_purchases=card.online_purchases,
        contactless_payments=card.contactless_payments,
        card_issue_date=card.card_issue_date,
        card_expiry_date=card.card_expiry_date,
        created_at=card.created_at
    )


@router.put("/{card_id}/limits", response_model=schemas.VirtualCardResponse)
async def update_card_limits(
    card_id: int,
    limits: schemas.CardLimitsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update card spending limits.
    """
    card = await services.CardService.update_card_limits(db, card_id, current_user.id, limits)
    
    card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
    
    return schemas.VirtualCardResponse(
        id=card.id,
        account_id=card.account_id,
        card_number_masked=mask_card_number(card_number),
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_status=card.card_status.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit,
        transaction_limit=card.transaction_limit,
        atm_withdrawal_limit=card.atm_withdrawal_limit,
        international_use=card.international_use,
        online_purchases=card.online_purchases,
        contactless_payments=card.contactless_payments,
        card_issue_date=card.card_issue_date,
        card_expiry_date=card.card_expiry_date,
        created_at=card.created_at
    )


@router.delete("/{card_id}", status_code=status.HTTP_200_OK)
async def cancel_card(
    card_id: int,
    cancellation_data: schemas.CardCancellationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel virtual card.
    
    - Cannot be undone
    - Card number cannot be reused
    """
    await services.CardService.cancel_card(db, card_id, current_user.id, cancellation_data)
    return {"message": "Card cancelled successfully"}


@router.post("/{card_id}/pin", status_code=status.HTTP_200_OK)
async def set_card_pin(
    card_id: int,
    pin_data: schemas.CardPINSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Set or change card PIN.
    
    - PIN must be 4-6 digits
    - PIN is hashed and stored securely
    """
    await services.CardService.set_card_pin(db, card_id, current_user.id, pin_data)
    return {"message": "PIN set successfully"}


@router.post("/{card_id}/cvv", response_model=schemas.CardCVVResponse)
async def get_card_cvv(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get card CVV (temporary display).
    
    - CVV shown for security verification
    - Recommend showing for limited time
    """
    # TODO: Implement CVV retrieval with time limit
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="CVV retrieval not yet implemented"
    )


@router.get("/{card_id}/transactions", status_code=status.HTTP_200_OK)
async def get_card_transactions(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get card transactions.
    """
    # TODO: Implement transaction retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transaction retrieval not yet implemented"
    )


@router.post("/{card_id}/dispute", status_code=status.HTTP_201_CREATED)
async def report_dispute(
    card_id: int,
    dispute_data: schemas.CardDisputeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Report disputed transaction.
    """
    # TODO: Implement dispute reporting
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Dispute reporting not yet implemented"
    )


@router.put("/{card_id}/controls", response_model=schemas.VirtualCardResponse)
async def update_card_controls(
    card_id: int,
    controls: schemas.CardControlsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update card controls (online/offline, international, contactless).
    """
    card = await services.CardService.update_card_controls(db, card_id, current_user.id, controls)
    
    card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
    
    return schemas.VirtualCardResponse(
        id=card.id,
        account_id=card.account_id,
        card_number_masked=mask_card_number(card_number),
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_status=card.card_status.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit,
        transaction_limit=card.transaction_limit,
        atm_withdrawal_limit=card.atm_withdrawal_limit,
        international_use=card.international_use,
        online_purchases=card.online_purchases,
        contactless_payments=card.contactless_payments,
        card_issue_date=card.card_issue_date,
        card_expiry_date=card.card_expiry_date,
        created_at=card.created_at
    )


@router.get("/{card_id}/security", response_model=schemas.CardSecurityStatusResponse)
async def get_card_security_status(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get card security status.
    """
    card = await services.CardService.get_card(db, card_id, current_user.id)
    
    return schemas.CardSecurityStatusResponse(
        card_id=card.id,
        card_status=card.card_status.value,
        fraud_alert_level=card.fraud_alert_level.value,
        pin_locked=card.pin_locked_until is not None and card.pin_locked_until > datetime.utcnow(),
        cvv_locked=card.cvv_locked_until is not None and card.cvv_locked_until > datetime.utcnow(),
        temp_lock_active=card.card_status == "blocked",
        temp_lock_expires_at=None,  # Would calculate from lock duration
        last_used_date=card.last_used_date
    )


@router.post("/{card_id}/temp-lock", response_model=schemas.VirtualCardResponse)
async def temp_lock_card(
    card_id: int,
    lock_data: schemas.CardTempLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Temporarily lock card.
    
    - Card auto-unlocks after specified duration
    - Useful for lost/misplaced cards
    """
    card = await services.CardService.temp_lock_card(db, card_id, current_user.id, lock_data)
    
    card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
    
    return schemas.VirtualCardResponse(
        id=card.id,
        account_id=card.account_id,
        card_number_masked=mask_card_number(card_number),
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_status=card.card_status.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit,
        transaction_limit=card.transaction_limit,
        atm_withdrawal_limit=card.atm_withdrawal_limit,
        international_use=card.international_use,
        online_purchases=card.online_purchases,
        contactless_payments=card.contactless_payments,
        card_issue_date=card.card_issue_date,
        card_expiry_date=card.card_expiry_date,
        created_at=card.created_at
    )


@router.post("/{card_id}/activate", response_model=schemas.VirtualCardResponse)
async def activate_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Activate card.
    """
    card = await services.CardService.activate_card(db, card_id, current_user.id)
    
    card_number = services.CardService.decrypt_card_number(card.card_number_encrypted)
    
    return schemas.VirtualCardResponse(
        id=card.id,
        account_id=card.account_id,
        card_number_masked=mask_card_number(card_number),
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        card_holder_name=card.card_holder_name,
        card_type=card.card_type.value,
        card_status=card.card_status.value,
        card_tier=card.card_tier.value,
        daily_spend_limit=card.daily_spend_limit,
        monthly_spend_limit=card.monthly_spend_limit,
        transaction_limit=card.transaction_limit,
        atm_withdrawal_limit=card.atm_withdrawal_limit,
        international_use=card.international_use,
        online_purchases=card.online_purchases,
        contactless_payments=card.contactless_payments,
        card_issue_date=card.card_issue_date,
        card_expiry_date=card.card_expiry_date,
        created_at=card.created_at
    )


@router.get("/{card_id}/balance", response_model=schemas.CardBalanceResponse)
async def get_card_balance(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get card available balance.
    """
    balance = await services.CardService.get_card_balance(db, card_id, current_user.id)
    return balance
