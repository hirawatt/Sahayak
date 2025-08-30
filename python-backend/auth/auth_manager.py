"""
Main Authentication Manager for Horizon Overlay.
Coordinates JWT handling, session management, and OAuth flow.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from .jwt_handler import JWTHandler
from .session_manager import SessionManager
from .oauth_client import OAuthClient

class AuthManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.jwt_handler = JWTHandler()
        self.session_manager = SessionManager()
        self.oauth_client = OAuthClient()
        self._current_user = None
        self._initialized = True
    
    async def start_auth_flow(self) -> Tuple[str, str]:
        """
        Start OAuth authentication flow.
        Returns (auth_url, state) for opening in browser.
        """
        return self.oauth_client.get_authorization_url()
    
    async def complete_auth_flow(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Complete OAuth flow with authorization code.
        Returns user data if successful.
        """
        # Exchange code for tokens
        token_data = await self.oauth_client.exchange_code_for_tokens(code, state)
        if not token_data:
            return None
        
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        
        if not access_token:
            return None
        
        # Get user info
        user_info = await self.oauth_client.get_user_info(access_token)
        if not user_info:
            return None
        
        user_id = user_info.get('id') or user_info.get('user_id')
        email = user_info.get('email')
        
        if not user_id or not email:
            return None
        
        # Calculate expiration
        expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Save session
        await self.session_manager.save_session(
            user_id=str(user_id),
            email=email,
            access_token=access_token,
            refresh_token=refresh_token or "",
            expires_at=expires_at,
            session_data=user_info
        )
        
        # Set current user
        self._current_user = {
            'user_id': str(user_id),
            'email': email,
            'access_token': access_token,
            'user_info': user_info
        }
        
        return self._current_user
    
    async def login_with_credentials(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Alternative login method for direct credentials (if supported).
        This is a placeholder for future implementation.
        """
        # This would implement direct login if the backend supports it
        # For now, we'll create a demo session
        user_id = f"demo-{email.split('@')[0]}"
        
        # Create tokens
        access_token = self.jwt_handler.create_access_token(user_id, email)
        refresh_token = self.jwt_handler.create_refresh_token(user_id)
        
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        user_info = {
            'id': user_id,
            'email': email,
            'name': email.split('@')[0].title(),
            'demo': True
        }
        
        await self.session_manager.save_session(
            user_id=user_id,
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            session_data=user_info
        )
        
        self._current_user = {
            'user_id': user_id,
            'email': email,
            'access_token': access_token,
            'user_info': user_info
        }
        
        return self._current_user
    
    async def restore_session(self) -> Optional[Dict[str, Any]]:
        """
        Restore user session from stored data.
        """
        session = await self.session_manager.get_current_session()
        if not session:
            return None
        
        user_id = session['user_id']
        access_token = session['access_token']
        
        # Verify token is still valid
        if self.jwt_handler.is_token_expired(access_token):
            # Try to refresh
            refresh_token = session['refresh_token']
            if refresh_token:
                new_access_token = await self.refresh_user_token(user_id)
                if new_access_token:
                    access_token = new_access_token
                else:
                    # Cannot refresh, session is invalid
                    await self.logout(user_id)
                    return None
            else:
                await self.logout(user_id)
                return None
        
        self._current_user = {
            'user_id': user_id,
            'email': session['email'],
            'access_token': access_token,
            'user_info': session['session_data']
        }
        
        return self._current_user
    
    async def refresh_user_token(self, user_id: str) -> Optional[str]:
        """
        Refresh access token for a user.
        """
        session = await self.session_manager.get_session(user_id)
        if not session:
            return None
        
        refresh_token = session['refresh_token']
        if not refresh_token:
            return None
        
        # Try OAuth refresh first
        token_data = await self.oauth_client.refresh_access_token(refresh_token)
        
        if token_data and token_data.get('access_token'):
            new_access_token = token_data['access_token']
            new_refresh_token = token_data.get('refresh_token', refresh_token)
            expires_in = token_data.get('expires_in', 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            # Fallback to JWT refresh
            new_access_token = self.jwt_handler.refresh_access_token(refresh_token)
            if not new_access_token:
                return None
            new_refresh_token = refresh_token
            expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        # Update session with new tokens
        await self.session_manager.update_tokens(
            user_id=user_id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_at=expires_at
        )
        
        return new_access_token
    
    async def logout(self, user_id: Optional[str] = None):
        """
        Logout user and clear session.
        """
        if user_id:
            await self.session_manager.delete_session(user_id)
        elif self._current_user:
            await self.session_manager.delete_session(self._current_user['user_id'])
        
        self._current_user = None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get currently authenticated user."""
        return self._current_user
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self._current_user is not None
    
    def get_access_token(self) -> Optional[str]:
        """Get current user's access token."""
        return self._current_user.get('access_token') if self._current_user else None
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return payload."""
        return self.jwt_handler.verify_token(token)
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions and OAuth states."""
        await self.session_manager.cleanup_expired_sessions()
        self.oauth_client.cleanup_expired_states()

# Global auth manager instance
auth_manager = AuthManager()