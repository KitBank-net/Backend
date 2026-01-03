"""
Developer Portal Router

Endpoints for third-party developer registration and app management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.modules.openbanking.schemas import (
    ThirdPartyAppCreate, ThirdPartyAppResponse, ThirdPartyAppCredentials,
    ThirdPartyAppUpdate, DeveloperRegisterRequest, DeveloperLoginRequest,
    DeveloperResponse, APIKeyResponse
)
from app.modules.openbanking.services import OpenBankingService
from app.modules.openbanking.models import AppStatus

router = APIRouter(prefix="/developers", tags=["open-banking-developers"])


# ============================================================
# Developer Registration (for independent developer portal)
# ============================================================

@router.post("/register", response_model=DeveloperResponse)
async def register_developer(
    data: DeveloperRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register as a developer.
    
    Developers can register to get access to the Open Banking APIs
    and create third-party applications.
    """
    from passlib.context import CryptContext
    from app.modules.users.models import User
    from sqlalchemy import select
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Check if email exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user as developer
    user = User(
        email=data.email,
        hashed_password=pwd_context.hash(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        is_developer=True  # Mark as developer
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return DeveloperResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        organization_name=data.organization_name,
        apps_count=0,
        created_at=user.created_at
    )


# ============================================================
# App Management
# ============================================================

@router.post("/apps", response_model=ThirdPartyAppCredentials)
async def register_app(
    data: ThirdPartyAppCreate,
    db: AsyncSession = Depends(get_db)
    # TODO: Add developer auth
):
    """
    Register a new third-party application.
    
    Returns client credentials (client_id and client_secret).
    The client_secret is only shown once - store it securely.
    """
    developer_id = 1  # TODO: Get from auth
    
    service = OpenBankingService(db)
    app, client_secret = await service.register_app(developer_id, data)
    
    return ThirdPartyAppCredentials(
        client_id=app.client_id,
        client_secret=client_secret
    )


@router.get("/apps", response_model=List[ThirdPartyAppResponse])
async def list_apps(
    db: AsyncSession = Depends(get_db)
    # TODO: Add developer auth
):
    """List developer's applications"""
    developer_id = 1  # TODO: Get from auth
    
    service = OpenBankingService(db)
    apps = await service.get_developer_apps(developer_id)
    
    return [ThirdPartyAppResponse.model_validate(app) for app in apps]


@router.get("/apps/{app_id}", response_model=ThirdPartyAppResponse)
async def get_app(
    app_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get application details"""
    from sqlalchemy import select
    from app.modules.openbanking.models import ThirdPartyApp
    
    result = await db.execute(
        select(ThirdPartyApp).where(ThirdPartyApp.id == app_id)
    )
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    return ThirdPartyAppResponse.model_validate(app)


@router.put("/apps/{app_id}", response_model=ThirdPartyAppResponse)
async def update_app(
    app_id: int,
    data: ThirdPartyAppUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update application details"""
    from sqlalchemy import select
    from app.modules.openbanking.models import ThirdPartyApp
    
    result = await db.execute(
        select(ThirdPartyApp).where(ThirdPartyApp.id == app_id)
    )
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    
    await db.commit()
    await db.refresh(app)
    
    return ThirdPartyAppResponse.model_validate(app)


@router.delete("/apps/{app_id}")
async def delete_app(
    app_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an application"""
    from sqlalchemy import select
    from app.modules.openbanking.models import ThirdPartyApp
    
    result = await db.execute(
        select(ThirdPartyApp).where(ThirdPartyApp.id == app_id)
    )
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    await db.delete(app)
    await db.commit()
    
    return {"message": "App deleted", "app_id": app_id}


@router.post("/apps/{app_id}/credentials", response_model=ThirdPartyAppCredentials)
async def regenerate_credentials(
    app_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate client credentials.
    
    This invalidates the previous client_secret.
    """
    developer_id = 1  # TODO: Get from auth
    
    service = OpenBankingService(db)
    
    try:
        client_id, client_secret = await service.regenerate_credentials(app_id, developer_id)
        return ThirdPartyAppCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/apps/{app_id}/submit-for-review")
async def submit_for_review(
    app_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit app for production review.
    
    Apps start in SANDBOX mode and must be reviewed before
    accessing production data.
    """
    from sqlalchemy import select
    from app.modules.openbanking.models import ThirdPartyApp
    
    result = await db.execute(
        select(ThirdPartyApp).where(ThirdPartyApp.id == app_id)
    )
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    if app.status != AppStatus.SANDBOX:
        raise HTTPException(status_code=400, detail="App is not in sandbox mode")
    
    # Check required fields
    if not app.privacy_policy_url:
        raise HTTPException(status_code=400, detail="Privacy policy URL required")
    if not app.redirect_uris:
        raise HTTPException(status_code=400, detail="At least one redirect URI required")
    
    app.status = AppStatus.PENDING
    await db.commit()
    
    return {
        "message": "App submitted for review",
        "app_id": app_id,
        "status": "pending"
    }


# ============================================================
# Sandbox
# ============================================================

@router.get("/sandbox/test-users")
async def get_sandbox_test_users():
    """Get available test users for sandbox environment"""
    return {
        "test_users": [
            {
                "username": "test_user_1",
                "password": "sandbox_pass_1",
                "description": "Basic user with 2 accounts"
            },
            {
                "username": "test_user_2",
                "password": "sandbox_pass_2",
                "description": "Premium user with 5 accounts and loans"
            },
            {
                "username": "test_user_3",
                "password": "sandbox_pass_3",
                "description": "Business user with business accounts"
            }
        ],
        "note": "These credentials only work in the sandbox environment"
    }


@router.post("/sandbox/reset")
async def reset_sandbox_data(
    db: AsyncSession = Depends(get_db)
):
    """Reset sandbox test data to default state"""
    # TODO: Implement sandbox data reset
    return {
        "message": "Sandbox data reset",
        "note": "Test accounts and transactions restored to default"
    }


# ============================================================
# API Documentation
# ============================================================

@router.get("/documentation")
async def get_api_documentation():
    """Get API documentation links"""
    return {
        "openapi_spec": "/openapi.json",
        "swagger_ui": "/docs",
        "redoc": "/redoc",
        "guides": {
            "getting_started": "https://kitbank.net/docs/getting-started",
            "authentication": "https://kitbank.net/docs/authentication",
            "consent_flow": "https://kitbank.net/docs/consent",
            "ais_api": "https://kitbank.net/docs/ais",
            "pis_api": "https://kitbank.net/docs/pis"
        },
        "support": {
            "email": "api-support@kitbank.net",
            "forum": "https://community.kitbank.net"
        }
    }
