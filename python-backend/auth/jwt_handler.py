"""
JWT Token Handler for Horizon Overlay Authentication.
Handles JWT token creation, validation, and refresh operations.
"""

import jwt
import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import json
import os

class JWTHandler:
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "horizon-overlay-secret-key-2025")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
    def create_access_token(self, user_id: str, email: str, additional_claims: Optional[Dict] = None) -> str:
        """Create a new access token for the user."""
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
            
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a new refresh token for the user."""
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create a new access token using a valid refresh token."""
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            return None
            
        user_id = payload.get("user_id")
        if not user_id:
            return None
            
        # For now, we'll use placeholder email - in real implementation,
        # this would be fetched from database
        return self.create_access_token(user_id, f"{user_id}@example.com")
    
    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired."""
        payload = self.verify_token(token)
        return payload is None