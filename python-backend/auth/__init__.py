"""
Authentication module for Horizon Overlay.
Provides JWT-based authentication, session management, and OAuth integration.
"""

from .auth_manager import AuthManager
from .jwt_handler import JWTHandler
from .session_manager import SessionManager
from .oauth_client import OAuthClient

__all__ = [
    "AuthManager",
    "JWTHandler", 
    "SessionManager",
    "OAuthClient"
]