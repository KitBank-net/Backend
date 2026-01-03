"""
Tests for Open Banking Gateway Module

Tests cover:
- Third-party app registration
- Consent management
- OAuth2 token flow
- OBP-compatible API endpoints
- Rate limiting
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.openbanking.models import (
    ThirdPartyApp, Consent, OAuthToken,
    ConsentType, ConsentStatus, AppStatus, TokenType, GrantType
)
from app.modules.openbanking.schemas import (
    ThirdPartyAppCreate, ConsentCreateRequest, ConsentPermissions,
    OBPAccountBasic, OBPAccountDetail
)
from app.modules.openbanking.services import OpenBankingService


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def app_create_data():
    """Sample third-party app registration data"""
    return ThirdPartyAppCreate(
        organization_name="Test Fintech Inc",
        organization_email="dev@testfintech.com",
        organization_website="https://testfintech.com",
        name="Test Budget App",
        description="A test budgeting application",
        logo_url="https://testfintech.com/logo.png",
        privacy_policy_url="https://testfintech.com/privacy",
        terms_of_service_url="https://testfintech.com/terms",
        redirect_uris=["https://testfintech.com/callback"],
        requested_scopes=["accounts", "balances", "transactions"],
        app_type="web"
    )


@pytest.fixture
def consent_create_data():
    """Sample consent request data"""
    return ConsentCreateRequest(
        consent_type=ConsentType.AIS,
        permissions=ConsentPermissions(
            accounts=True,
            balances=True,
            transactions=True,
            payments=False
        ),
        account_ids=None,
        valid_until=datetime.utcnow() + timedelta(days=90),
        frequency_per_day=4
    )


# ============================================================
# Third-Party App Tests
# ============================================================

class TestThirdPartyAppRegistration:
    """Tests for third-party app registration"""
    
    @pytest.mark.asyncio
    async def test_register_app_success(self, db_session: AsyncSession, test_user, app_create_data):
        """Test successful app registration"""
        service = OpenBankingService(db_session)
        
        app, client_secret = await service.register_app(test_user.id, app_create_data)
        
        assert app.id is not None
        assert app.name == "Test Budget App"
        assert app.client_id is not None
        assert len(app.client_id) > 20
        assert client_secret is not None
        assert len(client_secret) > 40
        assert app.status == AppStatus.SANDBOX
        assert "accounts" in app.allowed_scopes
    
    @pytest.mark.asyncio
    async def test_get_app_by_client_id(self, db_session: AsyncSession, test_user, app_create_data):
        """Test retrieving app by client_id"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        
        retrieved_app = await service.get_app_by_client_id(app.client_id)
        
        assert retrieved_app is not None
        assert retrieved_app.id == app.id
        assert retrieved_app.name == app.name
    
    @pytest.mark.asyncio
    async def test_get_app_invalid_client_id(self, db_session: AsyncSession):
        """Test retrieving app with invalid client_id returns None"""
        service = OpenBankingService(db_session)
        
        app = await service.get_app_by_client_id("invalid_client_id")
        
        assert app is None
    
    @pytest.mark.asyncio
    async def test_verify_client_credentials_success(self, db_session: AsyncSession, test_user, app_create_data):
        """Test verifying valid client credentials"""
        service = OpenBankingService(db_session)
        
        app, client_secret = await service.register_app(test_user.id, app_create_data)
        
        verified_app = await service.verify_client_credentials(app.client_id, client_secret)
        
        assert verified_app is not None
        assert verified_app.id == app.id
    
    @pytest.mark.asyncio
    async def test_verify_client_credentials_wrong_secret(self, db_session: AsyncSession, test_user, app_create_data):
        """Test verifying with wrong secret returns None"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        
        verified_app = await service.verify_client_credentials(app.client_id, "wrong_secret")
        
        assert verified_app is None
    
    @pytest.mark.asyncio
    async def test_regenerate_credentials(self, db_session: AsyncSession, test_user, app_create_data):
        """Test regenerating client credentials"""
        service = OpenBankingService(db_session)
        
        app, old_secret = await service.register_app(test_user.id, app_create_data)
        
        client_id, new_secret = await service.regenerate_credentials(app.id, test_user.id)
        
        assert client_id == app.client_id  # client_id unchanged
        assert new_secret != old_secret  # Secret changed
        
        # Old secret should no longer work
        old_verify = await service.verify_client_credentials(client_id, old_secret)
        assert old_verify is None
        
        # New secret should work
        new_verify = await service.verify_client_credentials(client_id, new_secret)
        assert new_verify is not None


# ============================================================
# Consent Management Tests
# ============================================================

class TestConsentManagement:
    """Tests for consent management"""
    
    @pytest.mark.asyncio
    async def test_create_consent_success(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test creating a consent"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        
        assert consent.id is not None
        assert consent.consent_id is not None
        assert consent.status == ConsentStatus.PENDING
        assert consent.consent_type == ConsentType.AIS
        assert consent.accounts_access is True
        assert consent.balances_access is True
        assert consent.payment_initiation is False
    
    @pytest.mark.asyncio
    async def test_get_consent(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test retrieving a consent by ID"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        created = await service.create_consent(app.id, test_user.id, consent_create_data)
        
        retrieved = await service.get_consent(created.consent_id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    @pytest.mark.asyncio
    async def test_authorize_consent(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test user authorizing a consent"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        
        authorized = await service.authorize_consent(
            consent.consent_id,
            test_user.id,
            authorized=True
        )
        
        assert authorized.status == ConsentStatus.AUTHORIZED
        assert authorized.authorization_code is not None
        assert authorized.authorized_at is not None
    
    @pytest.mark.asyncio
    async def test_reject_consent(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test user rejecting a consent"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        
        rejected = await service.authorize_consent(
            consent.consent_id,
            test_user.id,
            authorized=False
        )
        
        assert rejected.status == ConsentStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_revoke_consent(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test revoking an authorized consent"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        revoked = await service.revoke_consent(
            consent.consent_id,
            test_user.id,
            reason="User requested revocation"
        )
        
        assert revoked.status == ConsentStatus.REVOKED
        assert revoked.revoked_at is not None
        assert revoked.revocation_reason == "User requested revocation"
    
    @pytest.mark.asyncio
    async def test_validate_consent_valid(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test validating an authorized consent"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        is_valid = await service.validate_consent(consent.consent_id, ["accounts", "balances"])
        
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_consent_missing_scope(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test validating consent fails if required scope not granted"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        # payments scope was not granted
        is_valid = await service.validate_consent(consent.consent_id, ["payments"])
        
        assert is_valid is False


# ============================================================
# OAuth2 Token Tests
# ============================================================

class TestOAuthTokens:
    """Tests for OAuth2 token management"""
    
    @pytest.mark.asyncio
    async def test_exchange_authorization_code(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test exchanging authorization code for tokens"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        authorized = await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        access_token, refresh_token, expires_in = await service.exchange_authorization_code(
            app,
            authorized.authorization_code,
            "https://testfintech.com/callback"
        )
        
        assert access_token is not None
        assert refresh_token is not None
        assert expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_exchange_invalid_code(self, db_session: AsyncSession, test_user, app_create_data):
        """Test exchanging invalid code raises error"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        
        with pytest.raises(ValueError, match="Invalid authorization code"):
            await service.exchange_authorization_code(
                app,
                "invalid_code",
                "https://testfintech.com/callback"
            )
    
    @pytest.mark.asyncio
    async def test_validate_access_token(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test validating access token"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        authorized = await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        access_token, _, _ = await service.exchange_authorization_code(
            app,
            authorized.authorization_code,
            "https://testfintech.com/callback"
        )
        
        token_record = await service.validate_access_token(access_token, ["accounts"])
        
        assert token_record is not None
        assert token_record.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, db_session: AsyncSession):
        """Test validating invalid token returns None"""
        service = OpenBankingService(db_session)
        
        token_record = await service.validate_access_token("invalid_token")
        
        assert token_record is None
    
    @pytest.mark.asyncio
    async def test_refresh_access_token(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test refreshing access token"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        authorized = await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        access_token, refresh_token, _ = await service.exchange_authorization_code(
            app,
            authorized.authorization_code,
            "https://testfintech.com/callback"
        )
        
        new_access_token, expires_in = await service.refresh_access_token(app, refresh_token)
        
        assert new_access_token is not None
        assert new_access_token != access_token
        assert expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, db_session: AsyncSession, test_user, app_create_data, consent_create_data):
        """Test revoking a token"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        consent = await service.create_consent(app.id, test_user.id, consent_create_data)
        authorized = await service.authorize_consent(consent.consent_id, test_user.id, True)
        
        access_token, _, _ = await service.exchange_authorization_code(
            app,
            authorized.authorization_code,
            "https://testfintech.com/callback"
        )
        
        revoked = await service.revoke_token(access_token)
        
        assert revoked is True
        
        # Token should no longer be valid
        token_record = await service.validate_access_token(access_token)
        assert token_record is None


# ============================================================
# OBP Data Transformation Tests
# ============================================================

class TestOBPDataTransformation:
    """Tests for OBP-compatible data transformations"""
    
    @pytest.mark.asyncio
    async def test_get_user_accounts_obp(self, db_session: AsyncSession, test_user, test_account):
        """Test getting accounts in OBP format"""
        service = OpenBankingService(db_session)
        
        accounts = await service.get_user_accounts_obp(test_user.id)
        
        assert len(accounts) >= 1
        assert accounts[0].bank_id == "kitbank"
        assert accounts[0].id is not None
    
    @pytest.mark.asyncio
    async def test_get_account_detail_obp(self, db_session: AsyncSession, test_user, test_account):
        """Test getting account detail in OBP format"""
        service = OpenBankingService(db_session)
        
        account = await service.get_account_detail_obp(test_account.id, test_user.id)
        
        assert account is not None
        assert account.bank_id == "kitbank"
        assert account.number == test_account.account_number
        assert account.balance is not None
    
    @pytest.mark.asyncio
    async def test_get_account_detail_wrong_user(self, db_session: AsyncSession, test_user, test_account):
        """Test getting account for wrong user returns None"""
        service = OpenBankingService(db_session)
        
        account = await service.get_account_detail_obp(test_account.id, 99999)
        
        assert account is None


# ============================================================
# Rate Limiting Tests
# ============================================================

class TestRateLimiting:
    """Tests for rate limiting"""
    
    @pytest.mark.asyncio
    async def test_log_api_request(self, db_session: AsyncSession, test_user, app_create_data):
        """Test logging API requests"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        
        await service.log_api_request(
            app_id=app.id,
            user_id=test_user.id,
            endpoint="/obp/v5.1.0/my/accounts",
            method="GET",
            status_code=200,
            response_time_ms=150,
            client_ip="192.168.1.1"
        )
        
        # Should not raise
        assert True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, db_session: AsyncSession, test_user, app_create_data):
        """Test rate limit check when within limits"""
        service = OpenBankingService(db_session)
        
        app, _ = await service.register_app(test_user.id, app_create_data)
        
        allowed, remaining_minute, remaining_day = await service.check_rate_limit(
            app.id,
            limit_per_minute=60,
            limit_per_day=10000
        )
        
        assert allowed is True
        assert remaining_minute == 60
        assert remaining_day == 10000
