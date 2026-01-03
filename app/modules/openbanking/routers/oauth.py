"""
OAuth2 Provider Router

OAuth2 authorization server endpoints for third-party apps.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.modules.openbanking.schemas import (
    OAuth2TokenRequest, OAuth2TokenResponse, OAuth2Error,
    OAuth2UserInfo, OpenIDConfiguration
)
from app.modules.openbanking.services import OpenBankingService

router = APIRouter(tags=["open-banking-oauth"])


@router.get("/oauth/authorize")
async def authorize(
    response_type: str = Query("code"),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(...),
    consent_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 Authorization Endpoint.
    
    Redirects user to consent/login page, then back to redirect_uri with code.
    """
    service = OpenBankingService(db)
    
    # Verify client
    app = await service.get_app_by_client_id(client_id)
    if not app:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_client", "error_description": "Unknown client_id"}
        )
    
    # Verify redirect_uri
    if redirect_uri not in (app.redirect_uris or []):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "error_description": "Invalid redirect_uri"}
        )
    
    # In a real implementation, this would:
    # 1. Show consent page if consent_id provided, or
    # 2. Show login page, then consent page
    # 3. After authorization, redirect with code
    
    # For API-only implementation, return consent info
    if consent_id:
        consent = await service.get_consent(consent_id)
        if consent and consent.authorization_code:
            # Redirect with authorization code
            redirect_url = f"{redirect_uri}?code={consent.authorization_code}&state={state}"
            return RedirectResponse(url=redirect_url)
    
    # Return authorization page info (for frontend to render)
    return {
        "action": "authorize",
        "client_id": client_id,
        "app_name": app.name,
        "organization": app.organization_name,
        "scopes": scope.split(),
        "redirect_uri": redirect_uri,
        "state": state,
        "consent_url": f"/api/v1/consents?client_id={client_id}"
    }


@router.post("/oauth/token", response_model=OAuth2TokenResponse)
async def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    code_verifier: Optional[str] = Form(None),  # PKCE
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 Token Endpoint.
    
    Exchange authorization code for tokens, or refresh access token.
    """
    service = OpenBankingService(db)
    
    # Verify client credentials
    app = await service.verify_client_credentials(client_id, client_secret)
    if not app:
        raise HTTPException(
            status_code=401,
            detail="invalid_client"
        )
    
    try:
        if grant_type == "authorization_code":
            if not code:
                raise HTTPException(status_code=400, detail="Missing code")
            if not redirect_uri:
                raise HTTPException(status_code=400, detail="Missing redirect_uri")
            
            access_token, refresh_token_str, expires_in = await service.exchange_authorization_code(
                app, code, redirect_uri
            )
            
            return OAuth2TokenResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=expires_in,
                refresh_token=refresh_token_str,
                scope="accounts balances transactions"  # From consent
            )
        
        elif grant_type == "refresh_token":
            if not refresh_token:
                raise HTTPException(status_code=400, detail="Missing refresh_token")
            
            access_token, expires_in = await service.refresh_access_token(app, refresh_token)
            
            return OAuth2TokenResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=expires_in,
                scope="accounts balances transactions"
            )
        
        elif grant_type == "client_credentials":
            # For app-level access (not user-specific)
            # Limited scopes available
            raise HTTPException(
                status_code=400,
                detail="client_credentials grant not supported for user data access"
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported grant_type: {grant_type}"
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/oauth/revoke")
async def revoke_token(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 Token Revocation Endpoint.
    
    Revoke an access or refresh token.
    """
    service = OpenBankingService(db)
    
    # Verify client
    app = await service.verify_client_credentials(client_id, client_secret)
    if not app:
        raise HTTPException(status_code=401, detail="invalid_client")
    
    await service.revoke_token(token)
    
    return {"message": "Token revoked"}


@router.get("/oauth/userinfo", response_model=OAuth2UserInfo)
async def userinfo(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    OpenID Connect UserInfo Endpoint.
    
    Returns user information based on access token.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split(" ")[1]
    
    service = OpenBankingService(db)
    token_record = await service.validate_access_token(token)
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user info
    from sqlalchemy import select
    from app.modules.users.models import User
    
    result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return OAuth2UserInfo(
        sub=str(user.id),
        name=f"{user.first_name} {user.last_name}",
        email=user.email,
        email_verified=user.email_verified
    )


@router.get("/.well-known/openid-configuration", response_model=OpenIDConfiguration)
async def openid_configuration():
    """
    OpenID Connect Discovery Endpoint.
    
    Returns server configuration information.
    """
    base_url = "https://kitbank.net/api/v1"  # TODO: From settings
    
    return OpenIDConfiguration(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        userinfo_endpoint=f"{base_url}/oauth/userinfo",
        revocation_endpoint=f"{base_url}/oauth/revoke",
        jwks_uri=f"{base_url}/.well-known/jwks.json",
        response_types_supported=["code", "token"],
        subject_types_supported=["public"],
        id_token_signing_alg_values_supported=["RS256"],
        scopes_supported=["openid", "profile", "email", "accounts", "balances", "transactions", "payments"],
        token_endpoint_auth_methods_supported=["client_secret_basic", "client_secret_post"],
        claims_supported=["sub", "name", "email", "email_verified"],
        code_challenge_methods_supported=["S256"]
    )


@router.get("/.well-known/jwks.json")
async def jwks():
    """
    JSON Web Key Set Endpoint.
    
    Returns public keys for token verification.
    """
    # TODO: Implement actual JWKS
    return {
        "keys": []
    }
