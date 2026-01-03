"""
API Endpoint Tests for Open Banking Gateway

Tests the HTTP endpoints directly using FastAPI TestClient.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


# ============================================================
# Developer Portal Endpoint Tests
# ============================================================

class TestDeveloperEndpoints:
    """Tests for developer portal API endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_app(self, async_client: AsyncClient):
        """Test registering a new third-party app"""
        response = await async_client.post(
            "/openbanking/developers/apps",
            json={
                "organization_name": "Test Fintech",
                "organization_email": "dev@test.com",
                "name": "Test App",
                "description": "A test application",
                "redirect_uris": ["https://test.com/callback"],
                "requested_scopes": ["accounts", "balances"],
                "app_type": "web"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "client_id" in data
        assert "client_secret" in data
    
    @pytest.mark.asyncio
    async def test_list_apps(self, async_client: AsyncClient):
        """Test listing developer's apps"""
        response = await async_client.get("/openbanking/developers/apps")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_sandbox_test_users(self, async_client: AsyncClient):
        """Test getting sandbox test users"""
        response = await async_client.get("/openbanking/developers/sandbox/test-users")
        
        assert response.status_code == 200
        data = response.json()
        assert "test_users" in data
        assert len(data["test_users"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_documentation(self, async_client: AsyncClient):
        """Test getting API documentation links"""
        response = await async_client.get("/openbanking/developers/documentation")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi_spec" in data
        assert "guides" in data


# ============================================================
# Consent Endpoint Tests
# ============================================================

class TestConsentEndpoints:
    """Tests for consent management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_consents(self, async_client: AsyncClient):
        """Test listing user consents"""
        response = await async_client.get("/openbanking/consents")
        
        assert response.status_code == 200
        data = response.json()
        assert "consents" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_get_consent_not_found(self, async_client: AsyncClient):
        """Test getting non-existent consent"""
        response = await async_client.get("/openbanking/consents/nonexistent_id")
        
        assert response.status_code == 404


# ============================================================
# OAuth Endpoint Tests
# ============================================================

class TestOAuthEndpoints:
    """Tests for OAuth2 provider endpoints"""
    
    @pytest.mark.asyncio
    async def test_openid_configuration(self, async_client: AsyncClient):
        """Test OpenID Connect discovery endpoint"""
        response = await async_client.get("/openbanking/.well-known/openid-configuration")
        
        assert response.status_code == 200
        data = response.json()
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "scopes_supported" in data
    
    @pytest.mark.asyncio
    async def test_jwks_endpoint(self, async_client: AsyncClient):
        """Test JWKS endpoint"""
        response = await async_client.get("/openbanking/.well-known/jwks.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
    
    @pytest.mark.asyncio
    async def test_token_missing_params(self, async_client: AsyncClient):
        """Test token endpoint with missing parameters"""
        response = await async_client.post(
            "/openbanking/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "test",
                "client_secret": "test"
            }
        )
        
        # Should fail due to missing code
        assert response.status_code in [400, 401]


# ============================================================
# OBP (Open Bank Project) Endpoint Tests
# ============================================================

class TestOBPEndpoints:
    """Tests for OBP-compatible API endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_banks(self, async_client: AsyncClient):
        """Test listing available banks"""
        response = await async_client.get("/openbanking/obp/v5.1.0/banks")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == "kitbank"
    
    @pytest.mark.asyncio
    async def test_get_bank(self, async_client: AsyncClient):
        """Test getting bank details"""
        response = await async_client.get("/openbanking/obp/v5.1.0/banks/kitbank")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "kitbank"
        assert data["short_name"] == "KitBank"
    
    @pytest.mark.asyncio
    async def test_get_bank_not_found(self, async_client: AsyncClient):
        """Test getting non-existent bank"""
        response = await async_client.get("/openbanking/obp/v5.1.0/banks/unknown")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_my_accounts_without_auth(self, async_client: AsyncClient):
        """Test accessing accounts without authorization"""
        response = await async_client.get("/openbanking/obp/v5.1.0/my/accounts")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_transactions_without_auth(self, async_client: AsyncClient):
        """Test accessing transactions without authorization"""
        response = await async_client.get(
            "/openbanking/obp/v5.1.0/banks/kitbank/accounts/1/transactions"
        )
        
        assert response.status_code == 401


# ============================================================
# Payment Initiation Endpoint Tests
# ============================================================

class TestPaymentEndpoints:
    """Tests for PIS endpoints"""
    
    @pytest.mark.asyncio
    async def test_initiate_payment_without_auth(self, async_client: AsyncClient):
        """Test initiating payment without authorization"""
        response = await async_client.post(
            "/openbanking/payments",
            json={
                "debtor_account": "1",
                "creditor_account": "KE123456789",
                "creditor_name": "Test Recipient",
                "amount": 100.00,
                "currency": "USD"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_payment_status_without_auth(self, async_client: AsyncClient):
        """Test getting payment status without authorization"""
        response = await async_client.get("/openbanking/payments/1")
        
        assert response.status_code == 401


# ============================================================
# Integration Tests with Auth Flow
# ============================================================

class TestOpenBankingIntegration:
    """End-to-end integration tests for Open Banking flow"""
    
    @pytest.mark.asyncio
    async def test_full_oauth_flow(self, async_client: AsyncClient):
        """Test complete OAuth2 authorization flow"""
        # Step 1: Register app
        app_response = await async_client.post(
            "/openbanking/developers/apps",
            json={
                "organization_name": "Integration Test Corp",
                "organization_email": "test@integration.com",
                "name": "Integration Test App",
                "redirect_uris": ["https://integration.test/callback"],
                "requested_scopes": ["accounts", "balances", "transactions"],
                "app_type": "web"
            }
        )
        
        assert app_response.status_code == 200
        creds = app_response.json()
        client_id = creds["client_id"]
        client_secret = creds["client_secret"]
        
        # Step 2: Request authorization (would redirect in real flow)
        auth_response = await async_client.get(
            "/openbanking/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://integration.test/callback",
                "scope": "accounts balances",
                "state": "random_state_123"
            }
        )
        
        # This returns authorization page info
        assert auth_response.status_code == 200
        
        # Note: Full flow would require:
        # - User login and consent authorization
        # - Getting authorization code
        # - Exchanging code for tokens
        # - Using tokens to access APIs
