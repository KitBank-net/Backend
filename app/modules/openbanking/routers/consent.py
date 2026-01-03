"""
Consent Management Router

PSD2-compliant consent management for third-party access.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.modules.openbanking.schemas import (
    ConsentCreateRequest, ConsentResponse, ConsentListResponse,
    ConsentAuthorizationRequest
)
from app.modules.openbanking.services import OpenBankingService
from app.modules.openbanking.models import ConsentStatus

router = APIRouter(prefix="/consents", tags=["open-banking-consent"])


@router.post("", response_model=ConsentResponse)
async def create_consent(
    data: ConsentCreateRequest,
    client_id: str = Query(..., description="Third-party app client_id"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a consent request.
    
    Third-party apps call this to request access to user data.
    Returns a consent ID and authorization URL for user redirect.
    """
    service = OpenBankingService(db)
    
    # Verify app
    app = await service.get_app_by_client_id(client_id)
    if not app:
        raise HTTPException(status_code=401, detail="Invalid client_id")
    
    # For now, use a placeholder user_id (in production, extracted from auth)
    # This endpoint would typically be called after OAuth authorization
    user_id = 1  # TODO: Get from OAuth flow
    
    consent = await service.create_consent(app.id, user_id, data)
    
    base_url = "https://kitbank.net"  # TODO: From settings
    auth_url = f"{base_url}/api/v1/oauth/authorize?consent_id={consent.consent_id}&client_id={client_id}"
    
    return ConsentResponse(
        consent_id=consent.consent_id,
        consent_type=consent.consent_type,
        status=consent.status,
        accounts_access=consent.accounts_access,
        balances_access=consent.balances_access,
        transactions_access=consent.transactions_access,
        payment_initiation=consent.payment_initiation,
        valid_from=consent.valid_from,
        valid_until=consent.valid_until,
        authorization_url=auth_url
    )


@router.get("", response_model=ConsentListResponse)
async def list_consents(
    status: Optional[ConsentStatus] = None,
    db: AsyncSession = Depends(get_db)
    # TODO: Add user auth dependency
):
    """
    List user's consents.
    
    Users can view all consents they've granted to third-party apps.
    """
    service = OpenBankingService(db)
    
    user_id = 1  # TODO: Get from auth
    consents = await service.get_user_consents(user_id)
    
    # Filter by status if provided
    if status:
        consents = [c for c in consents if c.status == status]
    
    return ConsentListResponse(
        consents=[
            ConsentResponse(
                consent_id=c.consent_id,
                consent_type=c.consent_type,
                status=c.status,
                accounts_access=c.accounts_access,
                balances_access=c.balances_access,
                transactions_access=c.transactions_access,
                payment_initiation=c.payment_initiation,
                valid_from=c.valid_from,
                valid_until=c.valid_until
            ) for c in consents
        ],
        total=len(consents)
    )


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent(
    consent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get consent details"""
    service = OpenBankingService(db)
    consent = await service.get_consent(consent_id)
    
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    
    return ConsentResponse(
        consent_id=consent.consent_id,
        consent_type=consent.consent_type,
        status=consent.status,
        accounts_access=consent.accounts_access,
        balances_access=consent.balances_access,
        transactions_access=consent.transactions_access,
        payment_initiation=consent.payment_initiation,
        valid_from=consent.valid_from,
        valid_until=consent.valid_until
    )


@router.put("/{consent_id}/authorize")
async def authorize_consent(
    consent_id: str,
    authorized: bool = Query(...),
    selected_accounts: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    User authorizes or rejects a consent.
    
    This is called from the bank's authorization page.
    """
    service = OpenBankingService(db)
    
    user_id = 1  # TODO: Get from auth
    
    try:
        consent = await service.authorize_consent(
            consent_id, user_id, authorized, selected_accounts
        )
        
        return {
            "consent_id": consent.consent_id,
            "status": consent.status.value,
            "authorization_code": consent.authorization_code if authorized else None,
            "message": "Consent authorized" if authorized else "Consent rejected"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{consent_id}")
async def revoke_consent(
    consent_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke a consent.
    
    Users can revoke consent at any time, immediately revoking
    third-party access to their data.
    """
    service = OpenBankingService(db)
    
    user_id = 1  # TODO: Get from auth
    
    try:
        consent = await service.revoke_consent(consent_id, user_id, reason)
        return {
            "consent_id": consent.consent_id,
            "status": consent.status.value,
            "message": "Consent revoked successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
