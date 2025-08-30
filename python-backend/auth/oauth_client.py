"""
OAuth Client for Horizon Overlay Authentication.
Handles OAuth 2.0 flow integration with external providers.
"""

import aiohttp
import asyncio
import secrets
import hashlib
import base64
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs
import os

class OAuthClient:
    def __init__(self, 
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 redirect_uri: Optional[str] = None,
                 auth_base_url: Optional[str] = None,
                 token_url: Optional[str] = None):
        
        # Default to Constella's OAuth endpoints or environment variables
        self.client_id = client_id or os.getenv("OAUTH_CLIENT_ID", "horizon-overlay-client")
        self.client_secret = client_secret or os.getenv("OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/auth/callback")
        
        # Default OAuth endpoints (matching Swift implementation)
        self.auth_base_url = auth_base_url or "https://www.constella.app/auth/authorize"
        self.token_url = token_url or "https://www.constella.app/auth/token"
        
        self._state_store = {}  # Store PKCE state temporarily
    
    def _generate_pkce_challenge(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge for secure OAuth flow."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge
    
    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth authorization URL with PKCE.
        Returns (auth_url, state) tuple.
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        code_verifier, code_challenge = self._generate_pkce_challenge()
        
        # Store PKCE verifier temporarily
        self._state_store[state] = {
            'code_verifier': code_verifier,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'scope': 'read write'
        }
        
        auth_url = f"{self.auth_base_url}?{urlencode(params)}"
        return auth_url, state
    
    async def exchange_code_for_tokens(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens.
        """
        # Retrieve and validate stored PKCE verifier
        if state not in self._state_store:
            return None
        
        pkce_data = self._state_store.pop(state)
        code_verifier = pkce_data['code_verifier']
        
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'code_verifier': code_verifier
        }
        
        # Add client_secret if available (for confidential clients)
        if self.client_secret:
            token_data['client_secret'] = self.client_secret
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"OAuth token exchange failed: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"OAuth token exchange error: {e}")
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Use refresh token to get a new access token.
        """
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id
        }
        
        if self.client_secret:
            token_data['client_secret'] = self.client_secret
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            print(f"Token refresh error: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information using access token.
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {access_token}'}
                async with session.get(
                    "https://www.constella.app/auth/user",  # User info endpoint
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            print(f"User info fetch error: {e}")
            return None
    
    def cleanup_expired_states(self, max_age_seconds: int = 600):
        """
        Clean up expired PKCE state entries (older than 10 minutes by default).
        """
        current_time = asyncio.get_event_loop().time()
        expired_states = [
            state for state, data in self._state_store.items()
            if current_time - data['timestamp'] > max_age_seconds
        ]
        
        for state in expired_states:
            self._state_store.pop(state, None)