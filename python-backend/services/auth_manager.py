"""
Authentication Manager - Python equivalent of AuthManager.swift
Handles user authentication, token management, and session state
"""

import asyncio
import json
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt


class AuthManager:
    """Manages user authentication and session state"""
    
    def __init__(self):
        self.is_authenticated: bool = False
        self.user_data: Optional[Dict[str, Any]] = None
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # Auth storage path
        self.auth_file_path = Path.home() / ".horizon-ai" / "auth.json"
        self.auth_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # API endpoints (matching Swift APIConfig)
        self.base_url = "https://itzerhypergalaxy.online"
        self.auth_endpoint = f"{self.base_url}/auth"
        
    async def initialize(self):
        """Initialize auth manager and load saved credentials"""
        await self.load_saved_auth()
        
        if self.auth_token and not self.is_token_expired():
            # Validate existing token
            await self.validate_token()
        
        print(f"Auth Manager initialized - Authenticated: {self.is_authenticated}")
    
    async def authenticate(self, token: str) -> bool:
        """
        Authenticate user with provided token
        
        Args:
            token: Authentication token
            
        Returns:
            bool: True if authentication successful
        """
        try:
            # Validate token with backend
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    f"{self.auth_endpoint}/validate",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        user_data = await response.json()
                        
                        self.auth_token = token
                        self.user_data = user_data
                        self.is_authenticated = True
                        
                        # Calculate token expiry (assuming 24h default)
                        self.token_expires_at = datetime.now() + timedelta(hours=24)
                        
                        await self.save_auth()
                        return True
                    else:
                        print(f"Authentication failed: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    async def logout(self):
        """Logout user and clear authentication data"""
        self.is_authenticated = False
        self.user_data = None
        self.auth_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Clear saved auth
        if self.auth_file_path.exists():
            self.auth_file_path.unlink()
        
        print("User logged out successfully")
    
    async def refresh_authentication(self) -> bool:
        """
        Refresh authentication token
        
        Returns:
            bool: True if refresh successful
        """
        if not self.refresh_token:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                data = {"refresh_token": self.refresh_token}
                
                async with session.post(
                    f"{self.auth_endpoint}/refresh",
                    json=data
                ) as response:
                    
                    if response.status == 200:
                        auth_data = await response.json()
                        
                        self.auth_token = auth_data.get("access_token")
                        self.refresh_token = auth_data.get("refresh_token")
                        self.token_expires_at = datetime.now() + timedelta(
                            seconds=auth_data.get("expires_in", 86400)
                        )
                        
                        await self.save_auth()
                        return True
                    
                    return False
                    
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return False
    
    async def validate_token(self) -> bool:
        """
        Validate current token with backend
        
        Returns:
            bool: True if token is valid
        """
        if not self.auth_token:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                async with session.get(
                    f"{self.auth_endpoint}/validate",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        self.is_authenticated = True
                        return True
                    else:
                        self.is_authenticated = False
                        return False
                        
        except Exception as e:
            print(f"Token validation failed: {e}")
            self.is_authenticated = False
            return False
    
    def is_token_expired(self) -> bool:
        """Check if current token is expired"""
        if not self.token_expires_at:
            return True
        
        return datetime.now() >= self.token_expires_at
    
    async def ensure_authenticated(self) -> bool:
        """
        Ensure user is authenticated, refresh token if needed
        
        Returns:
            bool: True if user is authenticated
        """
        if not self.is_authenticated:
            return False
        
        if self.is_token_expired():
            success = await self.refresh_authentication()
            if not success:
                await self.logout()
                return False
        
        return True
    
    async def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests
        
        Returns:
            Dict[str, str]: Headers with authentication
        """
        if not await self.ensure_authenticated():
            return {}
        
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    async def save_auth(self):
        """Save authentication data to file"""
        auth_data = {
            "auth_token": self.auth_token,
            "refresh_token": self.refresh_token,
            "user_data": self.user_data,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "is_authenticated": self.is_authenticated
        }
        
        try:
            with open(self.auth_file_path, 'w') as f:
                json.dump(auth_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save auth data: {e}")
    
    async def load_saved_auth(self):
        """Load saved authentication data from file"""
        if not self.auth_file_path.exists():
            return
        
        try:
            with open(self.auth_file_path, 'r') as f:
                auth_data = json.load(f)
            
            self.auth_token = auth_data.get("auth_token")
            self.refresh_token = auth_data.get("refresh_token")
            self.user_data = auth_data.get("user_data")
            self.is_authenticated = auth_data.get("is_authenticated", False)
            
            expires_str = auth_data.get("token_expires_at")
            if expires_str:
                self.token_expires_at = datetime.fromisoformat(expires_str)
                
        except Exception as e:
            print(f"Failed to load saved auth: {e}")
            # Clear corrupted auth file
            if self.auth_file_path.exists():
                self.auth_file_path.unlink()
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        return self.user_data if self.is_authenticated else None
    
    def get_tenant_name(self) -> str:
        """Get tenant name for API requests"""
        if self.user_data:
            return self.user_data.get("tenant_name", "default")
        return "default"