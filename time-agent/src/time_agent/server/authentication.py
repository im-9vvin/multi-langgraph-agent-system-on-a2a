"""Authentication handling for the server."""

import logging
from typing import Optional

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
    
    async def authenticate(self, conn: HTTPConnection):
        """Authenticate a request.
        
        Args:
            conn: HTTP connection
            
        Returns:
            Tuple of (auth_credentials, user) or None
        """
        # For now, we'll implement a simple bearer token check
        # In production, this would validate against A2A auth standards
        
        auth_header = conn.headers.get("Authorization")
        
        if not auth_header:
            # No auth required for now (open access)
            return AuthCredentials(["unauthenticated"]), SimpleUser("anonymous")
        
        try:
            scheme, token = auth_header.split(" ", 1)
            
            if scheme.lower() != "bearer":
                return None
            
            # TODO: Validate token against A2A standards
            # For now, accept any bearer token
            
            return AuthCredentials(["authenticated"]), SimpleUser("a2a_client")
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError("Invalid authentication credentials")


def get_current_user(conn: HTTPConnection) -> Optional[str]:
    """Get current user from connection.
    
    Args:
        conn: HTTP connection
        
    Returns:
        Username or None
    """
    if hasattr(conn, "user") and conn.user.is_authenticated:
        return conn.user.username
    return None