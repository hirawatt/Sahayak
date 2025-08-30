"""
Backend client for communication with the Python backend service
"""

import logging
import asyncio
import json
from typing import Optional, Dict, Any, Callable
import aiohttp
import websockets
from dataclasses import dataclass

from config.settings import BackendConfig


@dataclass
class APIResponse:
    """Represents an API response"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class BackendClient:
    """Client for communicating with the Python backend"""
    
    def __init__(self, backend_config: BackendConfig):
        self.config = backend_config
        self.logger = logging.getLogger(__name__)
        
        # HTTP client
        self.session: Optional[aiohttp.ClientSession] = None
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_task: Optional[asyncio.Task] = None
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Connection state
        self.connected = False
        self.reconnect_attempts = 0
    
    async def connect(self):
        """Connect to the backend service"""
        self.logger.info("Connecting to backend service")
        
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=self.config.api_timeout)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            
            # Test HTTP connection
            health_response = await self.get("/api/v1/health")
            if not health_response.success:
                raise Exception("Backend health check failed")
            
            # Connect WebSocket
            await self._connect_websocket()
            
            self.connected = True
            self.reconnect_attempts = 0
            self.logger.info("Successfully connected to backend")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to backend: {e}")
            await self.disconnect()
            raise
    
    async def disconnect(self):
        """Disconnect from the backend service"""
        self.logger.info("Disconnecting from backend service")
        self.connected = False
        
        # Close WebSocket
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        # Close HTTP session
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _connect_websocket(self):
        """Connect to WebSocket endpoint"""
        try:
            self.websocket = await websockets.connect(self.config.websocket_url)
            self.ws_task = asyncio.create_task(self._websocket_listener())
            self.logger.info("WebSocket connected")
        except Exception as e:
            self.logger.error(f"Failed to connect WebSocket: {e}")
            raise
    
    async def _websocket_listener(self):
        """Listen for WebSocket messages"""
        try:
            while self.connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self._handle_websocket_message(message)
                except websockets.exceptions.ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    break
                except Exception as e:
                    self.logger.error(f"Error in WebSocket listener: {e}")
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if self.connected:
                # Try to reconnect
                asyncio.create_task(self._reconnect_websocket())
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(data)
            else:
                self.logger.debug(f"No handler for message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    async def _reconnect_websocket(self):
        """Attempt to reconnect WebSocket"""
        if self.reconnect_attempts >= self.config.reconnect_attempts:
            self.logger.error("Max reconnect attempts reached")
            return
        
        self.reconnect_attempts += 1
        wait_time = min(2 ** self.reconnect_attempts, 30)  # Exponential backoff
        
        self.logger.info(f"Reconnecting WebSocket in {wait_time}s (attempt {self.reconnect_attempts})")
        await asyncio.sleep(wait_time)
        
        try:
            await self._connect_websocket()
            self.reconnect_attempts = 0
            self.logger.info("WebSocket reconnected successfully")
        except Exception as e:
            self.logger.error(f"WebSocket reconnect failed: {e}")
            asyncio.create_task(self._reconnect_websocket())
    
    # HTTP API methods
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> APIResponse:
        """Make GET request"""
        return await self._request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> APIResponse:
        """Make POST request"""
        return await self._request("POST", endpoint, json=data)
    
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> APIResponse:
        """Make PUT request"""
        return await self._request("PUT", endpoint, json=data)
    
    async def delete(self, endpoint: str) -> APIResponse:
        """Make DELETE request"""
        return await self._request("DELETE", endpoint)
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """Make HTTP request"""
        if not self.session:
            return APIResponse(success=False, error="Not connected")
        
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    data = await response.text()
                
                if response.status < 400:
                    return APIResponse(success=True, data=data)
                else:
                    error_msg = data.get('error', f"HTTP {response.status}") if isinstance(data, dict) else str(data)
                    return APIResponse(success=False, error=error_msg)
                    
        except Exception as e:
            self.logger.error(f"Request failed: {method} {url} - {e}")
            return APIResponse(success=False, error=str(e))
    
    # WebSocket methods
    async def send_websocket_message(self, message_type: str, data: Dict[str, Any]):
        """Send message via WebSocket"""
        if not self.websocket:
            self.logger.error("WebSocket not connected")
            return
        
        message = {
            'type': message_type,
            'data': data
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket message: {e}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register handler for WebSocket message type"""
        self.message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")
    
    # AI/Chat specific methods
    async def send_chat_message(self, message: str, smarter_analysis: bool = False) -> APIResponse:
        """Send chat message to AI"""
        data = {
            'text': message,
            'smarter_analysis': smarter_analysis
        }
        return await self.post("/api/v1/ai/send-message", data)
    
    async def send_ai_message(self, text: str, smarter_analysis: bool = False) -> APIResponse:
        """Send message to AI - alias for send_chat_message"""
        return await self.send_chat_message(text, smarter_analysis)
    
    async def get_chat_history(self) -> APIResponse:
        """Get AI message history"""
        return await self.get("/api/v1/ai/messages")
    
    async def get_ai_messages(self) -> APIResponse:
        """Get AI messages - alias for get_chat_history"""
        return await self.get_chat_history()
    
    async def clear_chat_history(self) -> APIResponse:
        """Clear AI conversation history"""
        return await self.post("/api/v1/ai/clear-conversation")
    
    async def get_ai_status(self) -> APIResponse:
        """Get AI connection status"""
        return await self.get("/api/v1/ai/status")
    
    # Notes specific methods
    async def create_note(self, title: str, content: str, tags: Optional[list] = None) -> APIResponse:
        """Create a new note"""
        data = {
            'title': title,
            'content': content,
            'tags': tags or []
        }
        return await self.post("/notes", data)
    
    async def get_notes(self, query: Optional[str] = None, tags: Optional[list] = None) -> APIResponse:
        """Get notes with optional filtering"""
        params = {}
        if query:
            params['query'] = query
        if tags:
            params['tags'] = ','.join(tags)
        
        return await self.get("/notes", params)
    
    async def update_note(self, note_id: str, title: Optional[str] = None, 
                         content: Optional[str] = None, tags: Optional[list] = None) -> APIResponse:
        """Update existing note"""
        data = {}
        if title is not None:
            data['title'] = title
        if content is not None:
            data['content'] = content
        if tags is not None:
            data['tags'] = tags
        
        return await self.put(f"/notes/{note_id}", data)
    
    async def delete_note(self, note_id: str) -> APIResponse:
        """Delete note"""
        return await self.delete(f"/notes/{note_id}")
    
    # Context specific methods
    async def capture_context(self, capture_image: bool = True) -> APIResponse:
        """Capture current context"""
        params = {'capture_image': capture_image}
        return await self.post("/api/v1/context/capture", params)
    
    async def search_context(self, ocr_text: str, method: str = "sentence_chunks") -> APIResponse:
        """Search for context based on OCR text"""
        data = {
            'ocr_text': ocr_text,
            'method': method
        }
        return await self.post("/api/v1/context/search", data)
    
    async def get_context_notes(self) -> APIResponse:
        """Get current context notes"""
        return await self.get("/api/v1/context/notes")
    
    async def refresh_context(self) -> APIResponse:
        """Refresh context - captures current context and searches for notes"""
        try:
            # First capture current context
            capture_response = await self.capture_context(capture_image=True)
            if not capture_response.success:
                return capture_response
            
            # Extract OCR text from captured context
            context_data = capture_response.data.get('data', {})
            ocr_text = context_data.get('ocr_text', '')
            
            if ocr_text:
                # Search for context based on OCR text
                search_response = await self.search_context(ocr_text)
                if not search_response.success:
                    return search_response
            
            # Get the updated context notes
            notes_response = await self.get_context_notes()
            if notes_response.success:
                # Format response to match frontend expectations
                notes_data = notes_response.data.get('data', {})
                return APIResponse(
                    success=True,
                    data={
                        'items': notes_data.get('notes', []),
                        'context': context_data
                    }
                )
            
            return notes_response
            
        except Exception as e:
            self.logger.error(f"Error refreshing context: {e}")
            return APIResponse(success=False, error=str(e))
    
    async def get_context_suggestions(self, query: str) -> APIResponse:
        """Get context-based suggestions"""
        params = {'query': query}
        return await self.get("/api/v1/context/suggestions", params)
    
    # Overlay control methods
    async def toggle_ai_assist(self) -> APIResponse:
        """Toggle AI Assist overlay"""
        return await self.post("/api/v1/overlay/ai-assist/toggle")
    
    async def toggle_auto_context(self) -> APIResponse:
        """Toggle Auto Context overlay"""
        return await self.post("/api/v1/overlay/auto-context/toggle")
    
    async def toggle_quick_capture(self) -> APIResponse:
        """Toggle Quick Capture overlay"""
        return await self.post("/api/v1/overlay/quick-capture/toggle")
    
    async def get_overlay_states(self) -> APIResponse:
        """Get current overlay states"""
        return await self.get("/api/v1/overlay/states")
    
    # Tag management methods
    async def get_all_tags(self) -> APIResponse:
        """Get all tags"""
        return await self.get("/api/v1/tags")
    
    async def search_tags(self, query: str) -> APIResponse:
        """Search tags by name"""
        params = {'query': query}
        return await self.get("/api/v1/tags/search", params)
    
    async def get_tag(self, tag_id: str) -> APIResponse:
        """Get specific tag by ID"""
        return await self.get(f"/api/v1/tags/{tag_id}")
    
    async def refresh_tags(self) -> APIResponse:
        """Refresh tags from server"""
        return await self.post("/api/v1/tags/refresh")
    
    async def get_tag_status(self) -> APIResponse:
        """Get tag manager status"""
        return await self.get("/api/v1/tags/status")
    
    # System status methods
    async def get_system_status(self) -> APIResponse:
        """Get comprehensive system status"""
        return await self.get("/api/v1/system/status")
    
    async def get_hotkeys(self) -> APIResponse:
        """Get current hotkey shortcuts"""
        return await self.get("/api/v1/hotkeys")
    
    async def update_hotkey(self, action: str, key: str, modifiers: list) -> APIResponse:
        """Update hotkey shortcut for an action"""
        data = {
            'key': key,
            'modifiers': modifiers
        }
        return await self.post(f"/api/v1/hotkeys/{action}", data)
    
    # Auth methods
    async def login(self, token: str) -> APIResponse:
        """Login to backend"""
        data = {'token': token}
        return await self.post("/api/v1/auth/login", data)
    
    async def logout(self) -> APIResponse:
        """Logout from backend"""
        return await self.post("/api/v1/auth/logout")
    
    async def get_auth_status(self) -> APIResponse:
        """Get authentication status"""
        return await self.get("/api/v1/auth/status")