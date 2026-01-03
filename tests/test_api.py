"""
API endpoint tests for health and basic endpoints
"""
import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "KitBank" in data["message"]


class TestAuthRequired:
    """Tests that verify auth is required"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_loans_requires_auth(self, client):
        """Test that loans endpoint requires authentication"""
        response = await client.get("/loans/")
        
        # Should be 401 Unauthorized
        assert response.status_code == 401
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_transactions_requires_auth(self, client):
        """Test that transactions endpoint requires authentication"""
        response = await client.get("/transactions/")
        
        assert response.status_code == 401
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_accounts_requires_auth(self, client):
        """Test that accounts endpoint requires authentication"""
        response = await client.get("/accounts/")
        
        assert response.status_code == 401
