"""Tests for the auth module"""

import base64
from unittest.mock import AsyncMock

import aiohttp
import pytest

from pydhis2.core.auth import (
    BasicAuthProvider, TokenAuthProvider, 
    PATAuthProvider, SessionAuthProvider, AuthManager, create_auth_provider
)
from pydhis2.core.errors import AuthenticationError
from pydhis2.core.types import AuthMethod


class TestBasicAuthProvider:
    """Tests for the BasicAuthProvider class"""
    
    def test_init(self):
        """Test basic auth initialization"""
        provider = BasicAuthProvider("admin", "district")
        assert provider.username == "admin"
        assert provider.password == "district"
        assert provider._auth_header.startswith("Basic ")
    
    def test_encode_basic_auth(self):
        """Test basic auth encoding"""
        result = BasicAuthProvider._encode_basic_auth("admin", "district")
        
        # Decode and verify
        expected = base64.b64encode(b"admin:district").decode('ascii')
        assert result == f"Basic {expected}"
    
    async def test_get_headers(self):
        """Test getting authentication headers"""
        provider = BasicAuthProvider("admin", "district")
        headers = await provider.get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        
        # Verify the encoded credentials
        encoded_part = headers["Authorization"].split(" ")[1]
        decoded = base64.b64decode(encoded_part).decode('utf-8')
        assert decoded == "admin:district"
    
    async def test_refresh_if_needed(self):
        """Test refresh (should always return False for Basic auth)"""
        provider = BasicAuthProvider("admin", "district")
        result = await provider.refresh_if_needed()
        assert result is False
    
    async def test_is_valid(self):
        """Test validity check (should always return True for Basic auth)"""
        provider = BasicAuthProvider("admin", "district")
        result = await provider.is_valid()
        assert result is True


class TestTokenAuthProvider:
    """Tests for the TokenAuthProvider class"""
    
    def test_init(self):
        """Test token auth initialization"""
        provider = TokenAuthProvider("abc123token")
        assert provider.token == "abc123token"
        assert provider.token_type == "Bearer"
        assert provider._auth_header == "Bearer abc123token"
    
    def test_init_custom_type(self):
        """Test token auth with custom token type"""
        provider = TokenAuthProvider("abc123token", "Custom")
        assert provider.token_type == "Custom"
        assert provider._auth_header == "Custom abc123token"
    
    async def test_get_headers(self):
        """Test getting authentication headers"""
        provider = TokenAuthProvider("abc123token")
        headers = await provider.get_headers()
        
        assert headers == {"Authorization": "Bearer abc123token"}
    
    async def test_refresh_if_needed(self):
        """Test refresh (should always return False for token auth)"""
        provider = TokenAuthProvider("abc123token")
        result = await provider.refresh_if_needed()
        assert result is False
    
    async def test_is_valid(self):
        """Test validity check (should always return True for token auth)"""
        provider = TokenAuthProvider("abc123token")
        result = await provider.is_valid()
        assert result is True


class TestPATAuthProvider:
    """Tests for the Personal Access Token auth provider"""
    
    def test_init(self):
        """Test PAT auth initialization"""
        provider = PATAuthProvider("pat_token_123")
        assert provider.pat_token == "pat_token_123"
        assert provider._auth_header == "Bearer pat_token_123"
    
    async def test_get_headers(self):
        """Test getting authentication headers"""
        provider = PATAuthProvider("pat_token_123")
        headers = await provider.get_headers()
        
        assert headers == {"Authorization": "Bearer pat_token_123"}
    
    async def test_refresh_if_needed(self):
        """Test refresh (should always return False for PAT)"""
        provider = PATAuthProvider("pat_token_123")
        result = await provider.refresh_if_needed()
        assert result is False
    
    async def test_is_valid(self):
        """Test validity check (should always return True for PAT)"""
        provider = PATAuthProvider("pat_token_123")
        result = await provider.is_valid()
        assert result is True


class TestSessionAuthProvider:
    """Tests for the SessionAuthProvider class"""
    
    def setup_method(self):
        """Setup session provider"""
        self.mock_session = AsyncMock(spec=aiohttp.ClientSession)
        self.provider = SessionAuthProvider(
            session=self.mock_session,
            base_url="https://dhis2.example.com"
        )
    
    def test_init(self):
        """Test session provider initialization"""
        assert self.provider.session == self.mock_session
        assert self.provider.base_url == "https://dhis2.example.com"
        assert self.provider._authenticated is False
    
    async def test_login_success(self):
        """Test successful login"""
        # Mock successful login response
        mock_response = AsyncMock()
        mock_response.status = 200
        
        self.mock_session.post.return_value.__aenter__.return_value = mock_response
        self.mock_session.post.return_value.__aexit__.return_value = None
        
        await self.provider.login("admin", "district")
        
        assert self.provider._authenticated is True
        
        # Check login request
        self.mock_session.post.assert_called_once()
        call_args = self.mock_session.post.call_args
        assert "/dhis-web-commons-security/login.action" in call_args[0][0]
        assert call_args[1]['data']['j_username'] == 'admin'
        assert call_args[1]['data']['j_password'] == 'district'
    
    async def test_login_failure(self):
        """Test failed login"""
        # Mock failed login response
        mock_response = AsyncMock()
        mock_response.status = 401
        
        self.mock_session.post.return_value.__aenter__.return_value = mock_response
        self.mock_session.post.return_value.__aexit__.return_value = None
        
        with pytest.raises(AuthenticationError, match="Login failed with status 401"):
            await self.provider.login("admin", "wrong_password")
        
        assert self.provider._authenticated is False
    
    async def test_get_headers(self):
        """Test get headers (should return empty for session auth)"""
        headers = await self.provider.get_headers()
        assert headers == {}
    
    async def test_refresh_if_needed_valid_session(self):
        """Test refresh check with valid session"""
        # Mock successful /api/me response
        mock_response = AsyncMock()
        mock_response.status = 200
        
        self.mock_session.get.return_value.__aenter__.return_value = mock_response
        self.mock_session.get.return_value.__aexit__.return_value = None
        
        result = await self.provider.refresh_if_needed()
        
        assert result is True
        self.mock_session.get.assert_called_once_with("https://dhis2.example.com/api/me")
    
    async def test_refresh_if_needed_invalid_session(self):
        """Test refresh check with invalid session"""
        # Mock 401 Unauthorized response
        mock_response = AsyncMock()
        mock_response.status = 401
        
        self.mock_session.get.return_value.__aenter__.return_value = mock_response
        self.mock_session.get.return_value.__aexit__.return_value = None
        
        result = await self.provider.refresh_if_needed()
        
        assert result is False
        assert self.provider._authenticated is False
    
    async def test_refresh_if_needed_exception(self):
        """Test refresh check with exception"""
        self.mock_session.get.side_effect = Exception("Network error")
        
        result = await self.provider.refresh_if_needed()
        
        assert result is False
        assert self.provider._authenticated is False
    
    async def test_is_valid(self):
        """Test validity check"""
        # Initially not authenticated
        assert await self.provider.is_valid() is False
        
        # After successful login
        self.provider._authenticated = True
        assert await self.provider.is_valid() is True


class TestCreateAuthProvider:
    """Tests for the create_auth_provider factory function"""
    
    def test_create_basic_auth_tuple(self):
        """Test creating basic auth from tuple"""
        provider = create_auth_provider(("admin", "district"), AuthMethod.BASIC)
        
        assert isinstance(provider, BasicAuthProvider)
        assert provider.username == "admin"
        assert provider.password == "district"
    
    def test_create_token_auth_method(self):
        """Test creating token auth with TOKEN method"""
        provider = create_auth_provider("token123", AuthMethod.TOKEN)
        
        assert isinstance(provider, TokenAuthProvider)
        assert provider.token == "token123"
    
    def test_create_pat_auth_method(self):
        """Test creating PAT auth with PAT method"""
        provider = create_auth_provider("pat123", AuthMethod.PAT)
        
        assert isinstance(provider, PATAuthProvider)
        assert provider.pat_token == "pat123"
    
    def test_create_basic_auth_invalid_tuple(self):
        """Test creating basic auth with invalid tuple"""
        with pytest.raises(ValueError, match="Basic authentication requires"):
            create_auth_provider(("admin",), AuthMethod.BASIC)  # Single element tuple


class TestAuthIntegration:
    """Tests for auth integration scenarios"""
    
    async def test_basic_auth_workflow(self):
        """Test complete basic auth workflow"""
        provider = BasicAuthProvider("admin", "district")
        
        # Check validity
        assert await provider.is_valid() is True
        
        # Get headers
        headers = await provider.get_headers()
        assert "Authorization" in headers
        
        # Refresh (should be no-op)
        refreshed = await provider.refresh_if_needed()
        assert refreshed is False
    
    async def test_session_auth_workflow(self):
        """Test complete session auth workflow"""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        provider = SessionAuthProvider(mock_session, "https://dhis2.example.com")
        
        # Mock successful login
        mock_response = AsyncMock()
        mock_response.status = 200
        
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session.post.return_value.__aexit__.return_value = None
        
        await provider.login("admin", "district")
        
        # Check validity after login
        assert await provider.is_valid() is True
        
        # Get headers (should be empty for session auth)
        headers = await provider.get_headers()
        assert headers == {}
    
    async def test_auth_manager_workflow(self):
        """Test complete auth manager workflow"""
        basic_provider = BasicAuthProvider("admin", "district")
        manager = AuthManager(basic_provider)
        
        # Get headers
        headers = await manager.get_auth_headers()
        assert "Authorization" in headers
