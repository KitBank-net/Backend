"""
Open Banking Gateway - Pydantic Schemas

Schemas for consent management, OAuth2, OBP-compatible responses,
and developer portal operations.
"""
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.modules.openbanking.models import ConsentType, ConsentStatus, AppStatus


# ============================================================
# Third-Party App Schemas
# ============================================================

class ThirdPartyAppCreate(BaseModel):
    """Request to register a third-party app"""
    organization_name: str = Field(..., min_length=2, max_length=200)
    organization_email: EmailStr
    organization_website: Optional[str] = None
    
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    
    redirect_uris: List[str] = Field(default_factory=list)
    requested_scopes: List[str] = Field(default_factory=list)  # accounts, balances, transactions, payments
    app_type: str = "web"  # web, mobile, server


class ThirdPartyAppResponse(BaseModel):
    id: int
    organization_name: str
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    client_id: str
    allowed_scopes: List[str]
    status: AppStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class ThirdPartyAppCredentials(BaseModel):
    """Client credentials (shown only once after creation)"""
    client_id: str
    client_secret: str
    message: str = "Store these credentials securely. The client_secret will not be shown again."


class ThirdPartyAppUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    redirect_uris: Optional[List[str]] = None


# ============================================================
# Consent Schemas
# ============================================================

class ConsentPermissions(BaseModel):
    """Requested permissions for consent"""
    accounts: bool = False
    balances: bool = False
    transactions: bool = False
    payments: bool = False


class ConsentCreateRequest(BaseModel):
    """Request to create a consent"""
    consent_type: ConsentType
    permissions: ConsentPermissions
    account_ids: Optional[List[str]] = None  # Specific accounts or all
    valid_until: datetime
    frequency_per_day: int = Field(4, ge=1, le=10)  # PSD2 limit


class ConsentResponse(BaseModel):
    consent_id: str
    consent_type: ConsentType
    status: ConsentStatus
    
    accounts_access: bool
    balances_access: bool
    transactions_access: bool
    payment_initiation: bool
    
    valid_from: datetime
    valid_until: datetime
    
    authorization_url: Optional[str] = None  # For redirect to bank auth
    
    class Config:
        from_attributes = True


class ConsentListResponse(BaseModel):
    consents: List[ConsentResponse]
    total: int


class ConsentAuthorizationRequest(BaseModel):
    """User's consent authorization"""
    consent_id: str
    authorized: bool
    selected_accounts: Optional[List[str]] = None  # If user limits accounts


# ============================================================
# OAuth2 Schemas
# ============================================================

class OAuth2AuthorizeRequest(BaseModel):
    """OAuth2 authorization request parameters"""
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    scope: str  # Space-separated scopes
    state: str  # CSRF protection
    code_challenge: Optional[str] = None  # PKCE
    code_challenge_method: Optional[str] = None  # S256


class OAuth2TokenRequest(BaseModel):
    """OAuth2 token request"""
    grant_type: str  # authorization_code, refresh_token, client_credentials
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: str
    client_secret: str
    code_verifier: Optional[str] = None  # PKCE


class OAuth2TokenResponse(BaseModel):
    """OAuth2 token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # Seconds
    refresh_token: Optional[str] = None
    scope: str


class OAuth2Error(BaseModel):
    """OAuth2 error response"""
    error: str
    error_description: Optional[str] = None
    error_uri: Optional[str] = None


class OAuth2UserInfo(BaseModel):
    """OpenID Connect user info"""
    sub: str  # User ID
    name: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None


# ============================================================
# OBP (Open Bank Project) Compatible Schemas
# ============================================================

class OBPBankInfo(BaseModel):
    """OBP Bank information"""
    id: str = "kitbank"
    short_name: str = "KitBank"
    full_name: str = "KitBank Digital Banking"
    logo_url: Optional[str] = None
    website: str = "https://kitbank.net"


class OBPAccountBasic(BaseModel):
    """OBP Account basic info"""
    id: str
    bank_id: str = "kitbank"
    label: str  # Account name/label
    account_type: str
    account_routings: List[Dict[str, str]] = []  # IBAN, Account Number


class OBPAccountBalance(BaseModel):
    """OBP Account balance"""
    currency: str
    amount: str  # String for precision


class OBPAccountDetail(BaseModel):
    """OBP detailed account info"""
    id: str
    bank_id: str = "kitbank"
    label: str
    number: str  # Account number
    account_type: str
    balance: OBPAccountBalance
    IBAN: Optional[str] = None
    swift_bic: Optional[str] = None
    owners: List[Dict[str, str]] = []
    account_routings: List[Dict[str, str]] = []


class OBPTransaction(BaseModel):
    """OBP Transaction"""
    id: str
    bank_id: str = "kitbank"
    account_id: str
    this_account: Dict[str, Any]
    other_account: Dict[str, Any]
    details: Dict[str, Any]


class OBPTransactionList(BaseModel):
    """OBP Transaction list response"""
    transactions: List[OBPTransaction]


class OBPAccountList(BaseModel):
    """OBP Account list response"""
    accounts: List[OBPAccountBasic]


# ============================================================
# Payment Initiation (PIS) Schemas
# ============================================================

class PaymentInitiationRequest(BaseModel):
    """PSD2 Payment Initiation request"""
    debtor_account: str  # Account ID or IBAN
    creditor_account: str  # Recipient account/IBAN
    creditor_name: str
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    reference: Optional[str] = None
    description: Optional[str] = None
    
    # For future/scheduled payments
    execution_date: Optional[datetime] = None


class PaymentInitiationResponse(BaseModel):
    """Payment initiation response"""
    payment_id: str
    status: str  # pending, authorized, rejected, completed
    created_at: datetime
    
    debtor_account: str
    creditor_account: str
    creditor_name: str
    amount: Decimal
    currency: str
    
    authorization_url: Optional[str] = None  # SCA redirect


class PaymentStatusResponse(BaseModel):
    """Payment status response"""
    payment_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None


# ============================================================
# Developer Portal Schemas
# ============================================================

class DeveloperRegisterRequest(BaseModel):
    """Developer registration"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    organization_name: str
    intended_use: str  # Brief description of intended API use


class DeveloperLoginRequest(BaseModel):
    """Developer login"""
    email: EmailStr
    password: str


class DeveloperResponse(BaseModel):
    """Developer info"""
    id: int
    email: str
    first_name: str
    last_name: str
    organization_name: str
    apps_count: int = 0
    created_at: datetime


class APIKeyResponse(BaseModel):
    """API key for sandbox access"""
    api_key: str
    environment: str = "sandbox"
    created_at: datetime
    expires_at: Optional[datetime] = None


# ============================================================
# Well-Known Configuration
# ============================================================

class OpenIDConfiguration(BaseModel):
    """OpenID Connect discovery document"""
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    revocation_endpoint: str
    jwks_uri: str
    response_types_supported: List[str] = ["code", "token"]
    subject_types_supported: List[str] = ["public"]
    id_token_signing_alg_values_supported: List[str] = ["RS256"]
    scopes_supported: List[str] = ["openid", "profile", "email", "accounts", "balances", "transactions", "payments"]
    token_endpoint_auth_methods_supported: List[str] = ["client_secret_basic", "client_secret_post"]
    claims_supported: List[str] = ["sub", "name", "email", "email_verified"]
    code_challenge_methods_supported: List[str] = ["S256"]


# ============================================================
# Rate Limiting
# ============================================================

class RateLimitStatus(BaseModel):
    """Rate limit status for API consumers"""
    limit_per_minute: int
    limit_per_day: int
    remaining_minute: int
    remaining_day: int
    reset_minute: datetime
    reset_day: datetime
