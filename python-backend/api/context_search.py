"""
Context Search API - Python equivalent of ContextSearchAPI.swift
Handles real-time context search via WebSocket for note suggestions
"""

import asyncio
import json
import websockets
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from models.context_data import Note


class SearchMethod(Enum):
    """Search method types"""
    TOPIC_EXTRACTION = "topic_extraction"
    SENTENCE_CHUNKS = "sentence_chunks"
    
    @property
    def endpoint(self) -> str:
        """Get WebSocket endpoint for search method"""
        if self == SearchMethod.TOPIC_EXTRACTION:
            return "/horizon/context/context-search-ws-topic-extraction"
        else:
            return "/horizon/context/context-search-ws-sentence-chunks"


@dataclass
class ContextSearchRequest:
    """Request model for context search"""
    screen_ocr: str
    tenant_name: str


@dataclass
class ContextSearchResponse:
    """Response model for context search"""
    results: List[Note]
    total_results: int
    search_method: str
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextSearchResponse':
        """Create response from dictionary"""
        results = []
        for result_data in data.get('results', []):
            note = Note(
                id=result_data.get('id', ''),
                title=result_data.get('title', ''),
                content=result_data.get('content', ''),
                tags=result_data.get('tags', []),
                created_at=datetime.fromisoformat(result_data.get('created_at', datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(result_data.get('updated_at', datetime.now().isoformat())),
                uniqueid=result_data.get('uniqueid', result_data.get('id', ''))
            )
            results.append(note)
        
        return cls(
            results=results,
            total_results=data.get('total_results', len(results)),
            search_method=data.get('search_method', 'unknown'),
            timestamp=data.get('timestamp', datetime.now().isoformat())
        )


class ContextSearchAPI:
    """WebSocket-based context search API"""
    
    def __init__(self):
        # Connection state
        self.is_connected: bool = False
        self.is_searching: bool = False
        self.connection_error: Optional[Exception] = None
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.base_url = "wss://itzerhypergalaxy.online"
        self.current_endpoint: Optional[str] = None
        
        # Search results
        self.search_results: Optional[ContextSearchResponse] = None
        
        # Reconnection handling
        self.should_reconnect: bool = True
        self.reconnect_delay: float = 3.0
        
        # Background tasks
        self.receive_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.on_results_received: Optional[Callable[[ContextSearchResponse], None]] = None
        self.on_connection_changed: Optional[Callable[[bool], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
    
    async def connect_for_search(self, method: SearchMethod = SearchMethod.SENTENCE_CHUNKS):
        """Connect to context search WebSocket with specified method"""
        self.current_endpoint = method.endpoint
        await self.connect(self.current_endpoint)
    
    async def connect(self, endpoint: str):
        """Connect to WebSocket endpoint"""
        if self.websocket:
            await self.disconnect()
        
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"Connecting to context search API: {url}")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.connection_error = None
            
            # Start receiving messages
            self.receive_task = asyncio.create_task(self._receive_messages())
            
            if self.on_connection_changed:
                self.on_connection_changed(True)
            
            print("Successfully connected to context search API")
            
        except Exception as e:
            print(f"Failed to connect to context search API: {e}")
            self.is_connected = False
            self.connection_error = e
            
            if self.on_error:
                self.on_error(e)
            
            if self.should_reconnect:
                await self._schedule_reconnect()
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.should_reconnect = False
        
        if self.receive_task:
            self.receive_task.cancel()
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.is_connected = False
        
        if self.on_connection_changed:
            self.on_connection_changed(False)
    
    async def search_context(
        self,
        screen_ocr: str,
        tenant_name: str = "EJIy9EyNGpYRZdRx0vqb9SiBQZx1"
    ):
        """
        Search for context based on screen OCR
        
        Args:
            screen_ocr: OCR text from screen capture
            tenant_name: User tenant identifier
        """
        if not self.is_connected:
            print("WebSocket not connected. Attempting to connect...")
            await self.connect_for_search()
            
            # Retry after connection attempt
            if not self.is_connected:
                print("Failed to connect for search")
                return
        
        self.is_searching = True
        
        print(f"Sending context search request for: {screen_ocr[:100]}...")
        
        request = ContextSearchRequest(
            screen_ocr=screen_ocr,
            tenant_name=tenant_name
        )
        
        try:
            request_json = json.dumps(asdict(request))
            await self.websocket.send(request_json)
            
        except Exception as e:
            print(f"Error sending context search request: {e}")
            self.is_searching = False
            self.connection_error = e
            
            if self.on_error:
                self.on_error(e)
    
    async def _receive_messages(self):
        """Background task to receive WebSocket messages"""
        try:
            while self.websocket and self.is_connected:
                try:
                    message = await self.websocket.recv()
                    
                    if isinstance(message, str):
                        await self._handle_message(message)
                    elif isinstance(message, bytes):
                        # Try to decode bytes as text
                        try:
                            text_message = message.decode('utf-8')
                            await self._handle_message(text_message)
                        except UnicodeDecodeError:
                            print("Received non-text binary message")
                            
                except websockets.exceptions.ConnectionClosed:
                    print("Context search WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"Error receiving context search message: {e}")
                    break
                    
        except Exception as e:
            print(f"Context search receive task error: {e}")
        finally:
            self.is_connected = False
            if self.should_reconnect and self.current_endpoint:
                await self._schedule_reconnect()
    
    async def _handle_message(self, message: str):
        """Handle received WebSocket message"""
        try:
            # Try to parse as JSON response
            data = json.loads(message)
            
            # Check if it's an error response
            if 'error' in data:
                error_message = data['error']
                print(f"Context search error: {error_message}")
                
                error = Exception(error_message)
                self.connection_error = error
                self.is_searching = False
                
                if self.on_error:
                    self.on_error(error)
                return
            
            # Parse as search response
            response = ContextSearchResponse.from_dict(data)
            
            self.search_results = response
            self.is_searching = False
            
            print(f"Received {response.total_results} context search results")
            
            # Notify callback
            if self.on_results_received:
                self.on_results_received(response)
                
        except json.JSONDecodeError as e:
            print(f"Failed to decode context search response: {e}")
            self.is_searching = False
            
            if self.on_error:
                self.on_error(e)
        except Exception as e:
            print(f"Error handling context search message: {e}")
            self.is_searching = False
            
            if self.on_error:
                self.on_error(e)
    
    async def _schedule_reconnect(self):
        """Schedule reconnection attempt"""
        if not self.current_endpoint:
            return
        
        print(f"Scheduling context search reconnect in {self.reconnect_delay} seconds")
        await asyncio.sleep(self.reconnect_delay)
        
        if self.should_reconnect:
            await self.connect(self.current_endpoint)
    
    def set_results_callback(self, callback: Callable[[ContextSearchResponse], None]):
        """Set callback for search results"""
        self.on_results_received = callback
    
    def set_connection_callback(self, callback: Callable[[bool], None]):
        """Set callback for connection state changes"""
        self.on_connection_changed = callback
    
    def set_error_callback(self, callback: Callable[[Exception], None]):
        """Set callback for errors"""
        self.on_error = callback


class AutoContextManager:
    """
    Manager for integrating context search with overlays
    Python equivalent of AutoContextManager in Swift
    """
    
    def __init__(self):
        self.context_notes: List[Note] = []
        self.is_loading: bool = False
        self.error: Optional[Exception] = None
        
        # Context search API
        self.context_search_api = ContextSearchAPI()
        
        # Setup callbacks
        self.context_search_api.set_results_callback(self._on_search_results)
        self.context_search_api.set_connection_callback(self._on_connection_changed)
        self.context_search_api.set_error_callback(self._on_error)
        
        # Callbacks for UI updates
        self.on_notes_updated: Optional[Callable[[List[Note]], None]] = None
        self.on_loading_changed: Optional[Callable[[bool], None]] = None
        self.on_error_occurred: Optional[Callable[[Exception], None]] = None
    
    async def connect(self, method: SearchMethod = SearchMethod.SENTENCE_CHUNKS):
        """Connect to the WebSocket service"""
        await self.context_search_api.connect_for_search(method)
    
    async def search_context(self, screen_ocr: str):
        """Search for context notes based on screen OCR"""
        self.is_loading = True
        self.error = None
        
        if self.on_loading_changed:
            self.on_loading_changed(True)
        
        await self.context_search_api.search_context(screen_ocr)
    
    async def disconnect(self):
        """Disconnect from the WebSocket service"""
        await self.context_search_api.disconnect()
    
    def _on_search_results(self, response: ContextSearchResponse):
        """Handle search results"""
        self.context_notes = response.results
        self.is_loading = False
        
        if self.on_notes_updated:
            self.on_notes_updated(self.context_notes)
        
        if self.on_loading_changed:
            self.on_loading_changed(False)
    
    def _on_connection_changed(self, connected: bool):
        """Handle connection state changes"""
        if not connected:
            self.is_loading = False
            
            if self.on_loading_changed:
                self.on_loading_changed(False)
    
    def _on_error(self, error: Exception):
        """Handle errors"""
        self.error = error
        self.is_loading = False
        
        if self.on_error_occurred:
            self.on_error_occurred(error)
        
        if self.on_loading_changed:
            self.on_loading_changed(False)
    
    def set_notes_callback(self, callback: Callable[[List[Note]], None]):
        """Set callback for note updates"""
        self.on_notes_updated = callback
    
    def set_loading_callback(self, callback: Callable[[bool], None]):
        """Set callback for loading state changes"""
        self.on_loading_changed = callback
    
    def set_error_callback(self, callback: Callable[[Exception], None]):
        """Set callback for error occurrences"""
        self.on_error_occurred = callback