"""Authentication bridge between A2A and internal systems."""

import logging
from typing import Optional, Dict, Any

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)
from starlette.requests import HTTPConnection


logger = logging.getLogger(__name__)


class A2AAuthenticationBackend(AuthenticationBackend):
    """Authentication backend for A2A protocol."""
    
    async def authenticate(
        self, conn: HTTPConnection
    ) -> Optional[tuple[AuthCredentials, SimpleUser]]:
        """Authenticate request based on A2A protocol.
        
        Args:
            conn: HTTP connection
            
        Returns:
            Authentication credentials and user, or None
        """
        # Check for A2A authentication headers
        auth_header = conn.headers.get("X-A2A-Auth")
        if not auth_header:
            # No authentication provided
            return None
            
        try:
            # Parse A2A auth header
            auth_data = self._parse_auth_header(auth_header)
            
            # Validate authentication
            if not self._validate_auth(auth_data):
                raise AuthenticationError("Invalid A2A authentication")
                
            # Create credentials and user
            scopes = auth_data.get("scopes", ["authenticated"])
            username = auth_data.get("agent_id", "anonymous")
            
            return AuthCredentials(scopes), SimpleUser(username)
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(str(e))
            
    def _parse_auth_header(self, auth_header: str) -> Dict[str, Any]:
        """Parse A2A authentication header.
        
        Args:
            auth_header: Authentication header value
            
        Returns:
            Parsed authentication data
        """
        # Simple parsing for now
        # Format: "A2A agent_id=xxx,token=yyy,scopes=zzz"
        if not auth_header.startswith("A2A "):
            raise ValueError("Invalid auth header format")
            
        auth_str = auth_header[4:]  # Remove "A2A "
        auth_data = {}
        
        for part in auth_str.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                auth_data[key.strip()] = value.strip()
                
        return auth_data
        
    def _validate_auth(self, auth_data: Dict[str, Any]) -> bool:
        """Validate authentication data.
        
        Args:
            auth_data: Authentication data
            
        Returns:
            True if valid
        """
        # TODO: Implement actual validation
        # For now, just check required fields
        required_fields = ["agent_id", "token"]
        return all(field in auth_data for field in required_fields)


class AuthBridge:
    """Bridge between A2A authentication and internal systems."""
    
    def __init__(self):
        """Initialize authentication bridge."""
        self.backend = A2AAuthenticationBackend()
        
    async def authenticate_a2a_request(
        self, headers: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Authenticate A2A request.
        
        Args:
            headers: Request headers
            
        Returns:
            Authentication context or None
        """
        auth_header = headers.get("X-A2A-Auth")
        if not auth_header:
            return None
            
        try:
            auth_data = self.backend._parse_auth_header(auth_header)
            if self.backend._validate_auth(auth_data):
                return {
                    "authenticated": True,
                    "agent_id": auth_data.get("agent_id"),
                    "scopes": auth_data.get("scopes", "").split(",")
                }
        except Exception as e:
            logger.error(f"Auth bridge error: {e}")
            
        return None
        
    def create_a2a_auth_header(
        self, agent_id: str, token: str, scopes: Optional[list[str]] = None
    ) -> str:
        """Create A2A authentication header.
        
        Args:
            agent_id: Agent identifier
            token: Authentication token
            scopes: Optional scopes
            
        Returns:
            Authentication header value
        """
        parts = [
            f"agent_id={agent_id}",
            f"token={token}"
        ]
        
        if scopes:
            parts.append(f"scopes={','.join(scopes)}")
            
        return f"A2A {','.join(parts)}"