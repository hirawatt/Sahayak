"""
AI Connection Manager - Python equivalent of AIConnectionManager.swift
Handles WebSocket-based AI chat with streaming responses, message history, and reconnection
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import base64
import uuid


@dataclass
class AIMessage:
    """AI message model"""
    role: str  # "user" or "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AIMessageMetadata:
    """Metadata for AI messages"""
    ocr_text: Optional[str] = None
    selected_text: Optional[str] = None
    browser_url: Optional[str] = None


@dataclass
class AIRequest:
    """AI request model"""
    messages: List[Dict[str, Any]]
    image_bytes: Optional[str] = None  # Base64 encoded
    smarter_analysis_enabled: bool = False


@dataclass
class AIResponse:
    """AI response model"""
    content: str
    is_complete: bool = False


@dataclass
class MessageData:
    """UI message data"""
    id: str
    message: str
    is_user: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if not self.id:
            self.id = str(uuid.uuid4())


class AIConnectionManager:
    """Manages AI WebSocket connection with streaming responses"""
    
    def __init__(self):
        # Connection state
        self.is_connected: bool = False
        self.is_receiving: bool = False
        self.should_maintain_connection: bool = True
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_url = "wss://itzerhypergalaxy.online/horizon/assist/chat-ws"
        
        # Message handling
        self.message_stream: str = ""
        self.message_history: List[AIMessage] = []
        self.last_messages: List[MessageData] = []
        
        # Reconnection handling
        self.reconnection_attempts: int = 0
        self.max_reconnection_attempts: int = 10
        self.reconnection_delay: float = 1.0
        
        # Background tasks
        self.receive_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self.connection_monitor_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.on_message_received: Optional[Callable[[str], None]] = None
        self.on_connection_changed: Optional[Callable[[bool], None]] = None
        
    async def connect(self):
        """Connect to AI WebSocket service"""
        if self.websocket or not self.should_maintain_connection:
            return
        
        try:
            print(f"Connecting to AI service: {self.connection_url}")
            
            self.websocket = await websockets.connect(
                self.connection_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.reconnection_attempts = 0
            self.reconnection_delay = 1.0
            
            # Start background tasks
            self._start_receive_task()
            self._start_connection_monitor()
            
            if self.on_connection_changed:
                self.on_connection_changed(True)
            
            print("Successfully connected to AI service")
            
        except Exception as e:
            print(f"Failed to connect to AI service: {e}")
            self.is_connected = False
            
            if self.should_maintain_connection:
                await self._handle_connection_error(e)
    
    async def disconnect(self):
        """Disconnect from AI service"""
        self.should_maintain_connection = False
        
        # Cancel background tasks
        if self.receive_task:
            self.receive_task.cancel()
        if self.ping_task:
            self.ping_task.cancel()
        if self.connection_monitor_task:
            self.connection_monitor_task.cancel()
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.is_connected = False
        
        if self.on_connection_changed:
            self.on_connection_changed(False)
        
        print("Disconnected from AI service")
    
    async def send_message(
        self,
        text: str,
        ocr_text: Optional[str] = None,
        selected_text: Optional[str] = None,
        browser_url: Optional[str] = None,
        image_data: Optional[bytes] = None,
        smarter_analysis_enabled: bool = False
    ):
        """
        Send message to AI service
        
        Args:
            text: User message text
            ocr_text: OCR text from screen
            selected_text: Selected text
            browser_url: Current browser URL
            image_data: Screenshot image data
            smarter_analysis_enabled: Enable advanced analysis
        """
        if not self.is_connected:
            if self.should_maintain_connection:
                await self.connect()
            
            if not self.is_connected:
                raise ConnectionError("Not connected to AI service")
        
        # Add user message to history
        if self.message_stream:
            # Save previous assistant message
            self.last_messages.append(MessageData(
                id=str(uuid.uuid4()),
                message=self.message_stream,
                is_user=False
            ))
        
        # Add current user message
        self.last_messages.append(MessageData(
            id=str(uuid.uuid4()),
            message=text,
            is_user=True
        ))
        
        # Clear current stream
        self.message_stream = ""
        
        # Create message metadata
        metadata = AIMessageMetadata(
            ocr_text=ocr_text,
            selected_text=selected_text,
            browser_url=browser_url
        )
        
        # Create and store user message
        user_message = AIMessage(
            role="user",
            content=text,
            metadata=asdict(metadata) if any([ocr_text, selected_text, browser_url]) else None
        )
        self.message_history.append(user_message)
        
        # Prepare image data
        base64_image = None
        if image_data:
            base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Create request
        request = AIRequest(
            messages=[asdict(msg) for msg in self.message_history],
            image_bytes=base64_image,
            smarter_analysis_enabled=smarter_analysis_enabled
        )
        
        # Send request
        self.is_receiving = True
        request_json = json.dumps(asdict(request))
        
        try:
            await self.websocket.send(request_json)
        except Exception as e:
            self.is_receiving = False
            raise e
    
    def _start_receive_task(self):
        """Start background task to receive messages"""
        self.receive_task = asyncio.create_task(self._receive_messages())
    
    def _start_connection_monitor(self):
        """Start background task to monitor connection"""
        self.connection_monitor_task = asyncio.create_task(self._monitor_connection())
    
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
                    print("WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
                    
        except Exception as e:
            print(f"Receive task error: {e}")
        finally:
            if self.should_maintain_connection:
                await self._handle_connection_error(Exception("Connection lost"))
    
    async def _handle_text_message(self, message: str):
        """Handle received text message"""
        try:
            # Try to parse as JSON (complete response)
            response_data = json.loads(message)
            response = AIResponse(**response_data)
            
            self.message_stream = response.content
            
            if response.is_complete:
                self.is_receiving = False
                
                # Add assistant message to history
                assistant_message = AIMessage(
                    role="assistant",
                    content=response.content
                )
                self.message_history.append(assistant_message)
            
            # Notify callback
            if self.on_message_received:
                self.on_message_received(self.message_stream)
                
        except json.JSONDecodeError:
            # Handle streaming text (character by character)
            if self.is_receiving:
                self.is_receiving = False
                self.message_stream = message
            else:
                self.message_stream += message
                
                # Clean up whitespace before punctuation
                import re
                self.message_stream = re.sub(
                    r'\s+([,\'"`])$',
                    r'\1',
                    self.message_stream
                )
            
            # Notify callback
            if self.on_message_received:
                self.on_message_received(self.message_stream)
    
    async def _handle_binary_message(self, message: bytes):
        """Handle received binary message"""
        try:
            # Try to decode as JSON
            text_message = message.decode('utf-8')
            await self._handle_text_message(text_message)
        except UnicodeDecodeError:
            print("Received non-text binary message")
    
    async def _monitor_connection(self):
        """Monitor connection health and reconnect if needed"""
        while self.should_maintain_connection:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                if self.should_maintain_connection and not self.is_connected:
                    print("Connection lost, attempting to reconnect...")
                    await self._reconnect()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Connection monitor error: {e}")
    
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
            
            print(f"Reconnecting in {delay} seconds (attempt {self.reconnection_attempts}/{self.max_reconnection_attempts})")
            
            await asyncio.sleep(delay)
            await self._reconnect()
        else:
            print("Max reconnection attempts reached")
            self.reconnection_attempts = 0
    
    async def _reconnect(self):
        """Reconnect to AI service"""
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
        await self.connect()
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.message_history.clear()
        self.last_messages.clear()
        self.message_stream = ""
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status for debugging"""
        return {
            "connected": self.is_connected,
            "receiving": self.is_receiving,
            "should_maintain": self.should_maintain_connection,
            "reconnection_attempts": self.reconnection_attempts,
            "message_count": len(self.message_history)
        }
    
    def set_message_callback(self, callback: Callable[[str], None]):
        """Set callback for message updates"""
        self.on_message_received = callback
    
    def set_connection_callback(self, callback: Callable[[bool], None]):
        """Set callback for connection state changes"""
        self.on_connection_changed = callback