"""
Open Banking Gateway - Database Models

Implements PSD2-compliant consent management, third-party app registration,
and OAuth2 token management.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    Enum as SQLEnum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ============================================================
# Enums
# ============================================================

class ConsentType(str, enum.Enum):
    """Types of Open Banking consent"""
    AIS = "ais"  # Account Information Service
    PIS = "pis"  # Payment Initiation Service
    CBPII = "cbpii"  # Card-Based Payment Instrument Issuer
    COMBINED = "combined"  # AIS + PIS


class ConsentStatus(str, enum.Enum):
    """Consent lifecycle status"""
    PENDING = "pending"  # Awaiting user authorization
    AUTHORIZED = "authorized"  # User granted consent
    REJECTED = "rejected"  # User rejected consent
    REVOKED = "revoked"  # User revoked consent
    EXPIRED = "expired"  # Consent expired
    CONSUMED = "consumed"  # One-time consent used


class AppStatus(str, enum.Enum):
    """Third-party application status"""
    PENDING = "pending"  # Awaiting approval
    APPROVED = "approved"  # Approved for production
    SUSPENDED = "suspended"  # Temporarily suspended
    REVOKED = "revoked"  # Permanently revoked
    SANDBOX = "sandbox"  # Sandbox/testing only


class TokenType(str, enum.Enum):
    """OAuth token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    AUTHORIZATION_CODE = "authorization_code"


class GrantType(str, enum.Enum):
    """OAuth grant types"""
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"


# ============================================================
# Third-Party Application Model
# ============================================================

class ThirdPartyApp(Base):
    """Third-party application registration for Open Banking"""
    __tablename__ = "third_party_apps"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Developer/Organization info
    developer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_name = Column(String(200), nullable=False)
    organization_email = Column(String(255), nullable=False)
    organization_website = Column(String(500))
    
    # App details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    logo_url = Column(String(500))
    privacy_policy_url = Column(String(500))
    terms_of_service_url = Column(String(500))
    
    # OAuth credentials
    client_id = Column(String(64), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(255), nullable=False)
    
    # Redirect URIs (JSON array)
    redirect_uris = Column(JSON, default=list)
    
    # Allowed scopes
    allowed_scopes = Column(JSON, default=list)  # ["accounts", "balances", "transactions", "payments"]
    
    # App type and status
    app_type = Column(String(50), default="web")  # web, mobile, server
    status = Column(SQLEnum(AppStatus), default=AppStatus.PENDING)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Approval tracking
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(Integer, ForeignKey("admin_users.id"))
    rejection_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    developer = relationship("User", foreign_keys=[developer_id])
    consents = relationship("Consent", back_populates="app")
    tokens = relationship("OAuthToken", back_populates="app")
    
    __table_args__ = (
        Index("ix_third_party_apps_developer_id", "developer_id"),
        Index("ix_third_party_apps_status", "status"),
    )


# ============================================================
# Consent Model
# ============================================================

class Consent(Base):
    """User consent for third-party data access"""
    __tablename__ = "consents"
    
    id = Column(Integer, primary_key=True, index=True)
    consent_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # Parties
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    app_id = Column(Integer, ForeignKey("third_party_apps.id"), nullable=False)
    
    # Consent type and status
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    status = Column(SQLEnum(ConsentStatus), default=ConsentStatus.PENDING)
    
    # Permissions - AIS
    accounts_access = Column(Boolean, default=False)
    balances_access = Column(Boolean, default=False)
    transactions_access = Column(Boolean, default=False)
    
    # Permissions - PIS
    payment_initiation = Column(Boolean, default=False)
    payment_status = Column(Boolean, default=False)
    
    # Scope details (specific accounts if limited)
    account_ids = Column(JSON, default=list)  # Empty = all accounts
    
    # Frequency limits (for recurring access)
    frequency_per_day = Column(Integer, default=4)  # PSD2 default
    
    # Validity period
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    
    # Authorization tracking
    authorized_at = Column(DateTime(timezone=True))
    authorization_code = Column(String(64))  # Temporary code before token exchange
    authorization_code_expires = Column(DateTime(timezone=True))
    
    # Revocation
    revoked_at = Column(DateTime(timezone=True))
    revocation_reason = Column(String(255))
    
    # Usage tracking
    last_accessed_at = Column(DateTime(timezone=True))
    access_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    app = relationship("ThirdPartyApp", back_populates="consents")
    
    __table_args__ = (
        Index("ix_consents_user_id", "user_id"),
        Index("ix_consents_app_id", "app_id"),
        Index("ix_consents_status", "status"),
        Index("ix_consents_valid_until", "valid_until"),
    )


# ============================================================
# OAuth Token Model
# ============================================================

class OAuthToken(Base):
    """OAuth2 tokens for third-party apps"""
    __tablename__ = "oauth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Token association
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    app_id = Column(Integer, ForeignKey("third_party_apps.id"), nullable=False)
    consent_id = Column(Integer, ForeignKey("consents.id"))
    
    # Token details
    token_type = Column(SQLEnum(TokenType), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    
    # Grant type used
    grant_type = Column(SQLEnum(GrantType), nullable=False)
    
    # Scopes granted
    scopes = Column(JSON, default=list)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Refresh token linkage
    refresh_token_id = Column(Integer, ForeignKey("oauth_tokens.id"))
    
    # Revocation
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True))
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True))
    use_count = Column(Integer, default=0)
    
    # Client info
    client_ip = Column(String(45))
    user_agent = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    app = relationship("ThirdPartyApp", back_populates="tokens")
    consent = relationship("Consent", foreign_keys=[consent_id])
    
    __table_args__ = (
        Index("ix_oauth_tokens_user_id", "user_id"),
        Index("ix_oauth_tokens_app_id", "app_id"),
        Index("ix_oauth_tokens_expires_at", "expires_at"),
    )


# ============================================================
# API Request Log (for rate limiting and audit)
# ============================================================

class APIRequestLog(Base):
    """Log of API requests from third-party apps"""
    __tablename__ = "api_request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Request source
    app_id = Column(Integer, ForeignKey("third_party_apps.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    
    # Response
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer)
    
    # Client info
    client_ip = Column(String(45))
    
    # Timestamp
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_api_request_logs_app_id", "app_id"),
        Index("ix_api_request_logs_requested_at", "requested_at"),
    )


# ============================================================
# Sandbox Test Data
# ============================================================

class SandboxUser(Base):
    """Test users for sandbox environment"""
    __tablename__ = "sandbox_users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Test user details
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    
    # Test data configuration
    num_accounts = Column(Integer, default=2)
    num_transactions = Column(Integer, default=50)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
