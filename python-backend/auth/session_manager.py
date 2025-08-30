"""
Session Manager for Horizon Overlay Authentication.
Handles user session persistence using SQLite database.
"""

import aiosqlite
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import os

class SessionManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.expanduser("~/.config/horizon-overlay/sessions.db")
        self._ensure_db_directory()
        
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize_db(self):
        """Initialize the database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    access_token TEXT,
                    refresh_token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    session_data TEXT
                )
            """)
            await db.commit()
    
    async def save_session(self, user_id: str, email: str, access_token: str, 
                          refresh_token: str, expires_at: datetime, 
                          session_data: Optional[Dict] = None):
        """Save or update a user session."""
        await self.initialize_db()
        
        session_data_json = json.dumps(session_data) if session_data else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_sessions 
                (user_id, email, access_token, refresh_token, expires_at, session_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, email, access_token, refresh_token, expires_at, session_data_json))
            await db.commit()
    
    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user session by user_id."""
        await self.initialize_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM user_sessions WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    session_data = json.loads(row['session_data']) if row['session_data'] else {}
                    return {
                        'user_id': row['user_id'],
                        'email': row['email'],
                        'access_token': row['access_token'],
                        'refresh_token': row['refresh_token'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'expires_at': row['expires_at'],
                        'session_data': session_data
                    }
                return None
    
    async def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent active session."""
        await self.initialize_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM user_sessions 
                WHERE expires_at > CURRENT_TIMESTAMP 
                ORDER BY updated_at DESC 
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    session_data = json.loads(row['session_data']) if row['session_data'] else {}
                    return {
                        'user_id': row['user_id'],
                        'email': row['email'],
                        'access_token': row['access_token'],
                        'refresh_token': row['refresh_token'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'expires_at': row['expires_at'],
                        'session_data': session_data
                    }
                return None
    
    async def update_tokens(self, user_id: str, access_token: str, refresh_token: str, expires_at: datetime):
        """Update tokens for an existing session."""
        await self.initialize_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE user_sessions 
                SET access_token = ?, refresh_token = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (access_token, refresh_token, expires_at, user_id))
            await db.commit()
    
    async def delete_session(self, user_id: str):
        """Delete a user session."""
        await self.initialize_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions from database."""
        await self.initialize_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP")
            await db.commit()
    
    async def is_user_authenticated(self, user_id: str) -> bool:
        """Check if a user has a valid session."""
        session = await self.get_session(user_id)
        if not session:
            return False
            
        # Check if session is not expired
        expires_at = datetime.fromisoformat(session['expires_at'].replace('Z', '+00:00'))
        return expires_at > datetime.utcnow()