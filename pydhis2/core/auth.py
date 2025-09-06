"""Authentication module - Support for Basic, Token, PAT and other auth methods"""

import base64
from typing import Any, Dict, Optional, Tuple, Union
from abc import ABC, abstractmethod

import aiohttp
from pydantic import BaseModel

from pydhis2.core.errors import AuthenticationError
from pydhis2.core.types import AuthMethod


class AuthProvider(ABC):
    """Authentication provider abstract base class"""
    
    @abstractmethod
    async def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        pass
    
    @abstractmethod
    async def refresh_if_needed(self) -> bool:
        """If needed, refresh the authentication. Returns whether it was refreshed"""
        pass
    
    @abstractmethod
    async def is_valid(self) -> bool:
        """Check if the authentication is valid"""
        pass


class BasicAuthProvider(AuthProvider):
    """Basic authentication provider"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._auth_header = self._encode_basic_auth(username, password)
    
    @staticmethod
    def _encode_basic_auth(username: str, password: str) -> str:
        """Encode Basic authentication"""
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
        return f"Basic {encoded}"
    
    async def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        return {"Authorization": self._auth_header}
    
    async def refresh_if_needed(self) -> bool:
        """Basic auth does not need to be refreshed"""
        return False
    
    async def is_valid(self) -> bool:
        """Basic auth is always valid (assuming credentials are correct)"""
        return True


class TokenAuthProvider(AuthProvider):
    """Token authentication provider"""
    
    def __init__(self, token: str, token_type: str = "Bearer"):
        self.token = token
        self.token_type = token_type
        self._auth_header = f"{token_type} {token}"
    
    async def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        return {"Authorization": self._auth_header}
    
    async def refresh_if_needed(self) -> bool:
        """Token auth does not need to be refreshed (simple implementation)"""
        return False
    
    async def is_valid(self) -> bool:
        """Token auth is always valid (assuming token is correct)"""
        return True


class PATAuthProvider(AuthProvider):
    """Personal Access Token authentication provider"""
    
    def __init__(self, pat_token: str):
        self.pat_token = pat_token
        self._auth_header = f"Bearer {pat_token}"
    
    async def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        return {"Authorization": self._auth_header}
    
    async def refresh_if_needed(self) -> bool:
        """PAT auth does not need to be refreshed"""
        return False
    
    async def is_valid(self) -> bool:
        """PAT auth is always valid (assuming token is correct)"""
        return True


class SessionAuthProvider(AuthProvider):
    """Session authentication provider (supports JSESSIONID, etc.)"""
    
    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        self.session = session
        self.base_url = base_url
        self._authenticated = False
    
    async def login(self, username: str, password: str) -> None:
        """Login to get a session"""
        login_url = f"{self.base_url}/dhis-web-commons-security/login.action"
        
        async with self.session.post(
            login_url,
            data={
                'j_username': username,
                'j_password': password
            }
        ) as response:
            if response.status == 200:
                self._authenticated = True
            else:
                raise AuthenticationError(f"Login failed with status {response.status}")
    
    async def get_headers(self) -> Dict[str, str]:
        """Get authentication headers (session auth relies on cookies)"""
        return {}
    
    async def refresh_if_needed(self) -> bool:
        """Check if session needs to be refreshed"""
        # Simple implementation: check the /api/me endpoint
        try:
            async with self.session.get(f"{self.base_url}/api/me") as response:
                if response.status == 401:
                    self._authenticated = False
                    return False
                return True
        except Exception:
            self._authenticated = False
            return False
    
    async def is_valid(self) -> bool:
        """Check if the session is valid"""
        return self._authenticated


def create_auth_provider(
    auth: Union[Tuple[str, str], str],
    auth_method: AuthMethod = AuthMethod.BASIC,
    session: Optional[aiohttp.ClientSession] = None,
    base_url: Optional[str] = None
) -> AuthProvider:
    """Factory function: create an authentication provider based on configuration"""
    
    if auth_method == AuthMethod.BASIC:
        if not isinstance(auth, tuple) or len(auth) != 2:
            raise ValueError("Basic authentication requires a (username, password) tuple")
        return BasicAuthProvider(auth[0], auth[1])
    
    elif auth_method == AuthMethod.TOKEN:
        if not isinstance(auth, str):
            raise ValueError("Token authentication requires a string token")
        return TokenAuthProvider(auth)
    
    elif auth_method == AuthMethod.PAT:
        if not isinstance(auth, str):
            raise ValueError("PAT authentication requires a string token")
        return PATAuthProvider(auth)
    
    else:
        raise ValueError(f"Unsupported authentication method: {auth_method}")


class AuthManager:
    """Authentication manager - manages authentication providers and refresh logic"""
    
    def __init__(self, auth_provider: AuthProvider):
        self.auth_provider = auth_provider
        self._last_refresh_check = 0
        self._refresh_interval = 300  # Check every 5 minutes
    
    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers, refreshing if necessary"""
        import time
        
        current_time = time.time()
        if current_time - self._last_refresh_check > self._refresh_interval:
            await self.auth_provider.refresh_if_needed()
            self._last_refresh_check = current_time
        
        return await self.auth_provider.get_headers()
    
    async def validate_auth(self) -> bool:
        """Validate if the authentication is valid"""
        return await self.auth_provider.is_valid()
    
    async def force_refresh(self) -> bool:
        """Force a refresh of the authentication"""
        return await self.auth_provider.refresh_if_needed()
