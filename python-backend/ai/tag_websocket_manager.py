"""
Tag WebSocket Manager - Python equivalent of TagWebSocketManager.swift
Handles real-time tag management via WebSocket with CRUD operations
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from models.context_data import Tag


@dataclass
class GetAllTagsRequest:
    """Request model for getting all tags"""
    tenant_name: str


@dataclass
class GetAllTagsResponse:
    """Response model for getting all tags"""
    results: List[Dict[str, Any]]


@dataclass
class TagAPIData:
    """Tag data from API"""
    uniqueid: str
    name: str
    color: str
    
    def to_tag(self) -> Tag:
        """Convert to Tag model"""
        return Tag(
            id=self.uniqueid,
            name=self.name,
            color=self.color
        )


@dataclass
class TagUpdate:
    """WebSocket tag update message"""
    type: str
    action: Optional[str] = None  # "created", "updated", "deleted"
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    status: Optional[str] = None  # For connection messages
    tenant_name: Optional[str] = None


@dataclass
class TagData:
    """Tag data in WebSocket messages"""
    uniqueid: str
    name: Optional[str] = None
    color: Optional[str] = None
    
    def to_tag(self) -> Optional[Tag]:
        """Convert to Tag model"""
        if not self.name or not self.color:
            return None
        
        return Tag(
            id=self.uniqueid,
            name=self.name,
            color=self.color
        )


class TagWebSocketManager:
    """Manages real-time tag synchronization via WebSocket"""
    
    def __init__(self):
        # Connection state
        self.is_connected: bool = False
        self.is_loading: bool = False
        self.error: Optional[str] = None
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.base_url = "wss://test-server-7w76.onrender.com"
        self.base_http_url = "https://test-server-7w76.onrender.com"
        self.tenant_name: str = ""
        
        # HTTP client session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Tag data
        self.tags: List[Tag] = []
        self.last_tag_update: Optional[TagUpdate] = None
        
        # Reconnection handling
        self.should_maintain_connection: bool = True
        self.reconnection_attempts: int = 0
        self.max_reconnection_attempts: int = 10
        self.reconnection_delay: float = 1.0
        
        # Background tasks
        self.receive_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self.connection_monitor_task: Optional[asyncio.Task] = None
        
        # Event callbacks
        self.on_tag_created: Optional[Callable[[Tag], None]] = None
        self.on_tag_updated: Optional[Callable[[Tag], None]] = None
        self.on_tag_deleted: Optional[Callable[[str], None]] = None
        self.on_connection_changed: Optional[Callable[[bool], None]] = None
        self.on_tags_loaded: Optional[Callable[[List[Tag]], None]] = None
        self.on_error_occurred: Optional[Callable[[str], None]] = None
    
    async def initialize(self, tenant_name: str):
        """Initialize with tenant name - fetches all tags and starts WebSocket connection"""
        self.tenant_name = tenant_name
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self.http_session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            # First, fetch all existing tags
            await self.fetch_all_tags()
            
            # Then connect to WebSocket for real-time updates
            await self.connect(tenant_name)
            
        except Exception as e:
            print(f"Failed to initialize TagWebSocketManager: {e}")
            self.error = str(e)
            
            if self.on_error_occurred:
                self.on_error_occurred(str(e))
    
    async def fetch_all_tags(self):
        """Fetch all tags from the API"""
        self.is_loading = True
        self.error = None
        
        if not self.tenant_name:
            error_msg = "Tenant name not set"
            self.error = error_msg
            self.is_loading = False
            
            if self.on_error_occurred:
                self.on_error_occurred(error_msg)
            return
        
        if not self.http_session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            url = f"{self.base_http_url}/constella_db/tag/get_all_tags_for_user"
            
            request_data = GetAllTagsRequest(tenant_name=self.tenant_name)
            
            async with self.http_session.post(
                url,
                json=asdict(request_data),
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse tags
                    tags = []
                    for tag_data in data.get('results', []):
                        tag_api_data = TagAPIData(**tag_data)
                        tags.append(tag_api_data.to_tag())
                    
                    self.tags = tags
                    self.is_loading = False
                    
                    print(f"Loaded {len(tags)} tags")
                    
                    if self.on_tags_loaded:
                        self.on_tags_loaded(tags)
                    
                else:
                    error_msg = f"HTTP {response.status}"
                    self.error = error_msg
                    self.is_loading = False
                    
                    if self.on_error_occurred:
                        self.on_error_occurred(error_msg)
                        
        except Exception as e:
            error_msg = str(e)
            self.error = error_msg
            self.is_loading = False
            
            print(f"Failed to fetch tags: {e}")
            
            if self.on_error_occurred:
                self.on_error_occurred(error_msg)
    
    async def refresh_tags(self):
        """Refresh tags from the API"""
        try:
            await self.fetch_all_tags()
        except Exception as e:
            print(f"Failed to refresh tags: {e}")
    
    async def connect(self, tenant_name: str):
        """Connect to tag WebSocket"""
        if self.websocket or not self.should_maintain_connection:
            return
        
        self.tenant_name = tenant_name
        
        try:
            # Construct WebSocket URL with tenant name
            url = f"{self.base_url}/constella_db/tag/ws?tenant_name={tenant_name}"
            print(f"Connecting to tag WebSocket: {url}")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.reconnection_attempts = 0
            self.reconnection_delay = 1.0
            
            # Start background tasks
            self._start_ping_task()
            self._start_receive_task()
            self._start_connection_monitor()
            
            if self.on_connection_changed:
                self.on_connection_changed(True)
            
            print("Successfully connected to tag WebSocket")
            
        except Exception as e:
            print(f"Failed to connect to tag WebSocket: {e}")
            self.is_connected = False
            
            if self.should_maintain_connection:
                await self._handle_connection_error(e)
    
    async def disconnect(self):
        """Disconnect from tag WebSocket"""
        self.should_maintain_connection = False
        
        # Cancel background tasks
        if self.ping_task:
            self.ping_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()
        if self.connection_monitor_task:
            self.connection_monitor_task.cancel()
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
        
        self.is_connected = False
        
        if self.on_connection_changed:
            self.on_connection_changed(False)
        
        print("Disconnected from tag WebSocket")
    
    def _start_ping_task(self):
        """Start background ping task"""
        self.ping_task = asyncio.create_task(self._ping_loop())
    
    def _start_receive_task(self):
        """Start background receive task"""
        self.receive_task = asyncio.create_task(self._receive_messages())
    
    def _start_connection_monitor(self):
        """Start background connection monitor task"""
        self.connection_monitor_task = asyncio.create_task(self._monitor_connection())
    
    async def _ping_loop(self):
        """Background task to send periodic pings"""
        while self.websocket and self.should_maintain_connection:
            try:
                await asyncio.sleep(30)  # 30 seconds
                if self.websocket:
                    await self.websocket.send("ping")
            except Exception as e:
                print(f"Tag WebSocket ping failed: {e}")
                break
    
    async def _receive_messages(self):
        """Background task to receive WebSocket messages"""
        try:
            while self.websocket and self.should_maintain_connection:
                try:
                    message = await self.websocket.recv()
                    
                    if isinstance(message, str):
                        await self._handle_text_message(message)
                    elif isinstance(message, bytes):
                        await self._handle_binary_message(message)
                        
                except websockets.exceptions.ConnectionClosed:
                    print("Tag WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"Tag WebSocket receive error: {e}")
                    break
                    
        except Exception as e:
            print(f"Tag WebSocket receive task error: {e}")
        finally:
            if self.should_maintain_connection:
                await self._handle_connection_error(Exception("Connection lost"))
    
    async def _handle_text_message(self, message: str):
        """Handle received text message"""
        # Handle pong responses
        if message == "pong":
            return
        
        try:
            # Try to parse as JSON
            data = json.loads(message)
            update = TagUpdate(**data)
            await self._handle_tag_update(update)
            
        except json.JSONDecodeError:
            print(f"Failed to parse tag message: {message}")
        except Exception as e:
            print(f"Error handling tag message: {e}")
    
    async def _handle_binary_message(self, message: bytes):
        """Handle received binary message"""
        try:
            text_message = message.decode('utf-8')
            await self._handle_text_message(text_message)
        except UnicodeDecodeError:
            print("Received non-text binary message")
    
    async def _handle_tag_update(self, update: TagUpdate):
        """Handle tag update message"""
        self.last_tag_update = update
        
        if update.type == "connection":
            print(f"Tag WebSocket connected: {update.status}")
            
        elif update.type == "tag_update":
            if not update.action or not update.data:
                return
            
            tag_data = TagData(**update.data)
            
            if update.action == "created":
                if tag := tag_data.to_tag():
                    self._add_or_update_tag(tag)
                    
                    if self.on_tag_created:
                        self.on_tag_created(tag)
                        
            elif update.action == "updated":
                if tag := tag_data.to_tag():
                    self._add_or_update_tag(tag)
                    
                    if self.on_tag_updated:
                        self.on_tag_updated(tag)
                        
            elif update.action == "deleted":
                self._remove_tag(tag_data.uniqueid)
                
                if self.on_tag_deleted:
                    self.on_tag_deleted(tag_data.uniqueid)
                    
        elif update.type == "ping":
            # Server ping, no action needed
            pass
            
        else:
            print(f"Unknown tag update type: {update.type}")
    
    async def _monitor_connection(self):
        """Monitor connection health"""
        while self.should_maintain_connection:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                if self.should_maintain_connection and not self.is_connected:
                    print("Tag WebSocket connection lost, attempting to reconnect...")
                    await self._reconnect()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Tag WebSocket connection monitor error: {e}")
    
    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors with exponential backoff"""
        self.is_connected = False
        
        if self.on_connection_changed:
            self.on_connection_changed(False)
        
        if not self.should_maintain_connection:
            return
        
        if self.reconnection_attempts < self.max_reconnection_attempts:
            self.reconnection_attempts += 1
            delay = min(self.reconnection_delay * (2 ** (self.reconnection_attempts - 1)), 30.0)
            
            print(f"Tag WebSocket reconnecting in {delay} seconds (attempt {self.reconnection_attempts}/{self.max_reconnection_attempts})")
            
            await asyncio.sleep(delay)
            await self._reconnect()
        else:
            print("Tag WebSocket max reconnection attempts reached")
            self.reconnection_attempts = 0
    
    async def _reconnect(self):
        """Reconnect to tag WebSocket"""
        if not self.should_maintain_connection:
            return
        
        # Close existing connection
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        
        # Attempt to reconnect
        await self.connect(self.tenant_name)
    
    def _add_or_update_tag(self, tag: Tag):
        """Add or update a tag in the local collection"""
        # Find existing tag by ID
        for i, existing_tag in enumerate(self.tags):
            if existing_tag.id == tag.id:
                # Update existing tag
                self.tags[i] = tag
                print(f"Updated tag: {tag.name}")
                return
        
        # Add new tag
        self.tags.append(tag)
        print(f"Added new tag: {tag.name}")
    
    def _remove_tag(self, uniqueid: str):
        """Remove a tag from the local collection"""
        for i, tag in enumerate(self.tags):
            if tag.id == uniqueid:
                removed_tag = self.tags.pop(i)
                print(f"Removed tag: {removed_tag.name}")
                return
    
    def get_tag(self, uniqueid: str) -> Optional[Tag]:
        """Get tag by unique ID"""
        for tag in self.tags:
            if tag.id == uniqueid:
                return tag
        return None
    
    def get_tags_containing(self, search_text: str) -> List[Tag]:
        """Get tags by name (case-insensitive search)"""
        if not search_text:
            return self.tags.copy()
        
        search_text = search_text.lower()
        return [tag for tag in self.tags if search_text in tag.name.lower()]
    
    def set_tag_created_callback(self, callback: Callable[[Tag], None]):
        """Set callback for tag creation events"""
        self.on_tag_created = callback
    
    def set_tag_updated_callback(self, callback: Callable[[Tag], None]):
        """Set callback for tag update events"""
        self.on_tag_updated = callback
    
    def set_tag_deleted_callback(self, callback: Callable[[str], None]):
        """Set callback for tag deletion events"""
        self.on_tag_deleted = callback
    
    def set_connection_callback(self, callback: Callable[[bool], None]):
        """Set callback for connection state changes"""
        self.on_connection_changed = callback
    
    def set_tags_loaded_callback(self, callback: Callable[[List[Tag]], None]):
        """Set callback for when tags are loaded"""
        self.on_tags_loaded = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """Set callback for error events"""
        self.on_error_occurred = callback