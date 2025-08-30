#!/usr/bin/env python3
"""
Main FastAPI server for Horizon AI Assistant Backend
Converts Swift ConstellaHorizonApp.swift to Python FastAPI
"""

import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Core service managers
from services.context_manager import AIContextManager
from services.overlay_manager import OverlayManager
from services.input_manager import InputManager
from services.auth_manager import AuthManager

# AI and WebSocket managers
from ai.connection_manager import AIConnectionManager
from ai.tag_websocket_manager import TagWebSocketManager
from api.context_search import AutoContextManager
from api.routes import api_router

# New capture and system integration components
from capture.context_extractor import ContextExtractor
from capture.ocr_processor import OCRProcessor
from capture.screen_reader import ScreenReader

# Platform-specific screen capture
import sys
if sys.platform == "darwin":
    from capture.macos_capture import MacOSScreenCapture as ScreenCapture
else:
    from capture.wayland_capture import WaylandScreenCapture as ScreenCapture
from system.system_tray import SystemTrayManager
from system.notification_manager import NotificationManager
from system.permission_handler import PermissionHandler
from system.dbus_interface import DBusInterface

# Utilities
from utils.logging_config import setup_logging


class HorizonApp:
    """Main application class - Python equivalent of AppDelegate in Swift"""
    
    def __init__(self):
        # Core managers
        self.context_manager = AIContextManager()
        self.overlay_manager = OverlayManager()
        self.input_manager = InputManager()
        self.auth_manager = AuthManager()
        
        # AI and WebSocket managers
        self.ai_connection_manager = AIConnectionManager()
        self.tag_websocket_manager = TagWebSocketManager()
        self.auto_context_manager = AutoContextManager()
        
        # New capture system components
        self.context_extractor = ContextExtractor()
        self.screen_capture = ScreenCapture()
        self.ocr_processor = OCRProcessor()
        self.screen_reader = ScreenReader()
        
        # System integration components
        self.system_tray = SystemTrayManager()
        self.notification_manager = NotificationManager()
        self.permission_handler = PermissionHandler()
        self.dbus_interface = DBusInterface()
        
        # Application state
        self.is_initialized = False
        
    async def startup(self):
        """Initialize all managers - equivalent to applicationDidFinishLaunching"""
        try:
            # Setup logging
            setup_logging()
            print("🚀 Starting Horizon AI Assistant Backend...")
            
            # Phase 1: Check and setup system permissions
            print("📋 Checking system permissions...")
            await self.permission_handler.check_all_permissions()
            
            # Show permission report
            self.permission_handler.print_permission_report()
            
            # Setup required permissions
            success, failed = await self.permission_handler.setup_required_permissions()
            if not success:
                print(f"⚠️  Warning: Some required permissions are missing: {failed}")
                print("Some features may not work properly. Run with --setup-permissions to fix.")
            
            # Phase 2: Initialize core services
            print("🔧 Initializing core services...")
            
            # Initialize AuthManager first
            await self.auth_manager.initialize()
            
            # Initialize AI Connection Manager
            self.ai_connection_manager.set_message_callback(self._on_ai_message_received)
            self.ai_connection_manager.set_connection_callback(self._on_ai_connection_changed)
            await self.ai_connection_manager.connect()
            
            # Initialize Tag WebSocket Manager if authenticated
            if self.auth_manager.is_authenticated:
                tenant_name = self.auth_manager.get_tenant_name()
                await self.tag_websocket_manager.initialize(tenant_name)
            
            # Phase 3: Initialize system integration
            print("🖥️  Setting up system integration...")
            
            # Setup D-Bus interface
            dbus_success = await self.dbus_interface.setup()
            if dbus_success:
                self._register_dbus_callbacks()
            
            # Setup notification manager
            await self.notification_manager.setup()
            
            # Setup system tray
            tray_success = await self.system_tray.setup()
            if tray_success:
                self._register_tray_callbacks()
            
            # Phase 4: Initialize input and capture systems
            print("⌨️  Setting up input and capture systems...")
            
            # Setup input event manager (global hotkeys)
            await self.input_manager.setup()
            
            # Register hotkey callbacks
            self.input_manager.register_hotkey_callback('aiAssist', self._on_ai_assist_hotkey)
            self.input_manager.register_hotkey_callback('autoContext', self._on_auto_context_hotkey)
            self.input_manager.register_hotkey_callback('quickCapture', self._on_quick_capture_hotkey)
            
            # Phase 5: Setup overlay manager
            print("🎯 Setting up overlay manager...")
            await self.overlay_manager.setup()
            
            # Phase 6: Setup Auto Context Manager callbacks
            print("🔍 Setting up context management...")
            self.auto_context_manager.set_notes_callback(self._on_context_notes_updated)
            self.auto_context_manager.set_loading_callback(self._on_context_loading_changed)
            self.auto_context_manager.set_error_callback(self._on_context_error)
            
            # Phase 7: Send startup notification
            await self.notification_manager.send_startup_notification()
            
            self.is_initialized = True
            print("✅ Horizon AI Assistant Backend started successfully!")
            
            # Show system status
            await self._print_system_status()
            
        except Exception as e:
            print(f"❌ Failed to start Horizon AI Assistant: {e}")
            await self.notification_manager.send_error_notification(
                "Startup Error", 
                f"Failed to start Horizon AI Assistant: {str(e)}"
            )
            raise
    
    async def _print_system_status(self):
        """Print comprehensive system status."""
        print("\n" + "="*60)
        print("🌟 HORIZON AI ASSISTANT - SYSTEM STATUS")
        print("="*60)
        
        # Core services
        print(f"🔐 Authentication: {'✅ Active' if self.auth_manager.is_authenticated else '❌ Inactive'}")
        print(f"🤖 AI Connection: {'✅ Connected' if self.ai_connection_manager.is_connected else '❌ Disconnected'}")
        print(f"🏷️  Tag Manager: {'✅ Connected' if self.tag_websocket_manager.is_connected else '❌ Disconnected'}")
        
        # System integration
        print(f"🔧 D-Bus Interface: {'✅ Active' if self.dbus_interface.is_running else '❌ Inactive'}")
        print(f"🔔 Notifications: {'✅ Enabled' if self.notification_manager.is_enabled() else '❌ Disabled'}")
        print(f"📊 System Tray: {'✅ Active' if self.system_tray.is_active else '❌ Inactive'}")
        
        # Input and capture
        print(f"⌨️  Input Manager: {'✅ Active' if hasattr(self.input_manager, 'hotkey_manager') else '❌ Inactive'}")
        print(f"📸 Screen Capture: {'✅ Available' if hasattr(self.screen_capture, 'screenshot_interface') else '❌ Unavailable'}")
        print(f"👁️  OCR Processor: {'✅ Ready' if hasattr(self.ocr_processor, 'thread_pool') else '❌ Not Ready'}")
        
        # Show available endpoints
        print(f"\n🌐 API Server: http://127.0.0.1:8000")
        print(f"📡 WebSocket: ws://127.0.0.1:8000/ws")
        print(f"📖 API Docs: http://127.0.0.1:8000/docs")
        
        print("="*60 + "\n")
    
    def _register_dbus_callbacks(self):
        """Register D-Bus method callbacks."""
        self.dbus_interface.register_callback('toggle_overlay', self._dbus_toggle_overlay)
        self.dbus_interface.register_callback('send_ai_message', self._dbus_send_ai_message)
        self.dbus_interface.register_callback('capture_context', self._dbus_capture_context)
    
    def _register_tray_callbacks(self):
        """Register system tray callbacks."""
        self.system_tray.register_callback('menu_item_clicked', self._on_tray_menu_item_clicked)
        self.system_tray.register_callback('settings_clicked', self._on_tray_settings_clicked)
        self.system_tray.register_callback('quit_clicked', self._on_tray_quit_clicked)
    
    async def shutdown(self):
        """Cleanup resources - equivalent to applicationWillTerminate"""
        print("🛑 Shutting down Horizon AI Assistant...")
        
        try:
            # Disconnect AI services
            await self.ai_connection_manager.disconnect()
            await self.tag_websocket_manager.disconnect()
            await self.auto_context_manager.disconnect()
            
            # Cleanup system integration
            await self.system_tray.cleanup()
            await self.notification_manager.cleanup()
            await self.dbus_interface.cleanup()
            
            # Cleanup input and capture systems
            await self.input_manager.cleanup()
            self.context_extractor.cleanup()
            self.screen_capture.cleanup()
            self.ocr_processor.cleanup()
            self.screen_reader.cleanup()
            
            # Cleanup other managers
            await self.overlay_manager.cleanup()
            
            print("✅ Horizon AI Assistant shutdown complete")
            
        except Exception as e:
            print(f"⚠️  Error during shutdown: {e}")
    
    # Hotkey callback methods
    async def _on_ai_assist_hotkey(self):
        """Handle AI Assist hotkey - equivalent to Swift shortcut handling"""
        try:
            # Capture current context using new context extractor
            context_data = await self.context_extractor.extract_context(capture_image=True)
            
            # Update context manager with extracted data
            await self.context_manager.update_context(
                ocr_text=context_data.primary_content,
                selected_text=context_data.application_context.get('selected_text', ''),
                browser_url=context_data.application_context.get('browser_url', ''),
                image_data=None  # Image data handled internally
            )
            
            # Toggle AI Assist overlay
            result = await self.overlay_manager.toggle_ai_assist()
            
            # Send notification
            await self.notification_manager.send_overlay_status_notification(
                "AI Assist", 
                result.get('state', False)
            )
            
            # Emit D-Bus signal
            self.dbus_interface.emit_overlay_state_changed("ai_assist", result.get('state', False))
            
            print("🤖 AI Assist activated with context")
            
        except Exception as e:
            print(f"Error in AI Assist hotkey: {e}")
            await self.notification_manager.send_error_notification(
                "AI Assist Error", 
                f"Failed to activate AI Assist: {str(e)}"
            )
    
    async def _on_auto_context_hotkey(self):
        """Handle Auto Context hotkey"""
        try:
            # Capture current context for search
            context_data = await self.context_extractor.extract_context(capture_image=True, analyze_deep=True)
            
            # Connect to context search if not already connected
            if not self.auto_context_manager.context_search_api.is_connected:
                await self.auto_context_manager.connect()
            
            # Search for relevant context using extracted content
            if context_data.primary_content:
                await self.auto_context_manager.search_context(context_data.primary_content)
            
            # Toggle Auto Context overlay
            result = await self.overlay_manager.toggle_auto_context()
            
            # Send notification
            await self.notification_manager.send_overlay_status_notification(
                "Auto Context", 
                result.get('state', False)
            )
            
            # Emit D-Bus signal
            self.dbus_interface.emit_overlay_state_changed("auto_context", result.get('state', False))
            
        except Exception as e:
            print(f"Error in Auto Context hotkey: {e}")
            await self.notification_manager.send_error_notification(
                "Auto Context Error", 
                f"Failed to activate Auto Context: {str(e)}"
            )
    
    async def _on_quick_capture_hotkey(self):
        """Handle Quick Capture hotkey"""
        try:
            # Capture screenshot and extract context
            context_data = await self.context_extractor.extract_context(capture_image=True)
            
            # Toggle Quick Capture overlay
            result = await self.overlay_manager.toggle_quick_capture()
            
            # Send notification
            await self.notification_manager.send_overlay_status_notification(
                "Quick Capture", 
                result.get('state', False)
            )
            
            # Emit D-Bus signal
            self.dbus_interface.emit_overlay_state_changed("quick_capture", result.get('state', False))
            
        except Exception as e:
            print(f"Error in Quick Capture hotkey: {e}")
    
    # AI callback methods
    def _on_ai_message_received(self, message: str):
        """Handle AI message updates"""
        try:
            # Send notification for AI response
            asyncio.create_task(
                self.notification_manager.send_ai_response_notification(message)
            )
            
            # Emit D-Bus signal
            self.dbus_interface.emit_ai_response_received(message)
            
            print(f"🤖 AI Message: {message[:100]}...")
            
        except Exception as e:
            print(f"Error handling AI message: {e}")
    
    def _on_ai_connection_changed(self, connected: bool):
        """Handle AI connection state changes"""
        status = "Connected" if connected else "Disconnected"
        print(f"🔗 AI Connection: {status}")
        
        # Update D-Bus status
        self.dbus_interface.update_status({"ai_connected": connected})
    
    # Context callback methods
    def _on_context_notes_updated(self, notes):
        """Handle context notes updates"""
        try:
            count = len(notes) if notes else 0
            print(f"📝 Context notes updated: {count} notes found")
            
            # Send notification
            asyncio.create_task(
                self.notification_manager.send_context_update_notification("notes", count)
            )
            
            # Emit D-Bus signal
            self.dbus_interface.emit_context_updated(f"{count} notes found")
            
        except Exception as e:
            print(f"Error handling context notes update: {e}")
    
    def _on_context_loading_changed(self, loading: bool):
        """Handle context loading state changes"""
        status = "Loading..." if loading else "Complete"
        print(f"🔍 Context search: {status}")
    
    def _on_context_error(self, error: Exception):
        """Handle context search errors"""
        print(f"❌ Context search error: {error}")
        asyncio.create_task(
            self.notification_manager.send_error_notification(
                "Context Search Error", 
                str(error)
            )
        )
    
    # D-Bus callback methods
    async def _dbus_toggle_overlay(self, overlay_name: str) -> bool:
        """Handle D-Bus overlay toggle request."""
        try:
            if overlay_name == "ai_assist":
                result = await self.overlay_manager.toggle_ai_assist()
            elif overlay_name == "auto_context":
                result = await self.overlay_manager.toggle_auto_context()
            elif overlay_name == "quick_capture":
                result = await self.overlay_manager.toggle_quick_capture()
            else:
                return False
            
            return result.get('state', False)
            
        except Exception as e:
            print(f"D-Bus toggle overlay error: {e}")
            return False
    
    async def _dbus_send_ai_message(self, message: str, context: str) -> bool:
        """Handle D-Bus AI message request."""
        try:
            await self.send_ai_message(message, False)
            return True
        except Exception as e:
            print(f"D-Bus send AI message error: {e}")
            return False
    
    async def _dbus_capture_context(self) -> bool:
        """Handle D-Bus context capture request."""
        try:
            context_data = await self.context_extractor.extract_context(capture_image=True)
            return True
        except Exception as e:
            print(f"D-Bus capture context error: {e}")
            return False
    
    # System tray callback methods
    async def _on_tray_menu_item_clicked(self, action: str):
        """Handle system tray menu item clicks."""
        try:
            if action == "toggle_ai_assist":
                await self._on_ai_assist_hotkey()
            elif action == "toggle_auto_context":
                await self._on_auto_context_hotkey()
            elif action == "toggle_quick_capture":
                await self._on_quick_capture_hotkey()
            elif action == "show_about":
                await self.notification_manager.send_quick_notification(
                    "About Horizon AI Assistant",
                    "AI-powered desktop overlay assistant for enhanced productivity"
                )
        except Exception as e:
            print(f"Tray menu action error: {e}")
    
    def _on_tray_settings_clicked(self):
        """Handle system tray settings click."""
        print("🔧 Opening settings... (Not implemented yet)")
    
    def _on_tray_quit_clicked(self):
        """Handle system tray quit click."""
        print("👋 Quit requested from system tray")
        # This would typically trigger application shutdown
    
    async def send_ai_message(self, text: str, smarter_analysis: bool = False):
        """Send message to AI service with current context"""
        try:
            # Capture current context using context extractor
            context_data = await self.context_extractor.extract_context(capture_image=True)
            
            # Send to AI with extracted context
            await self.ai_connection_manager.send_message(
                text=text,
                ocr_text=context_data.primary_content,
                selected_text=context_data.application_context.get('selected_text', ''),
                browser_url=context_data.application_context.get('browser_url', ''),
                image_data=None,  # Handled internally by context extractor
                smarter_analysis_enabled=smarter_analysis
            )
            
        except Exception as e:
            print(f"Error sending AI message: {e}")
            raise


# Create global app instance
horizon_app = HorizonApp()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    # Startup
    await horizon_app.startup()
    yield
    # Shutdown
    await horizon_app.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Horizon AI Assistant API",
    description="Backend API for Horizon AI Assistant Desktop Application",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for PyQt6 frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with PyQt6 frontend"""
    await websocket.accept()
    
    # Register this websocket with overlay manager for real-time updates
    horizon_app.overlay_manager.add_websocket_connection(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle WebSocket messages from PyQt6 frontend
            import json
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format"
                }))
    except WebSocketDisconnect:
        horizon_app.overlay_manager.remove_websocket_connection(websocket)
        print("WebSocket disconnected")


async def handle_websocket_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages from PyQt6 frontend"""
    import json
    
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong"}))
    
    elif message_type == "get_context":
        # Request for current context
        context_data = await horizon_app.context_manager.capture_current_context()
        await websocket.send_text(json.dumps({
            "type": "context_data",
            "data": {
                "selected_text": context_data.selected_text,
                "ocr_text": context_data.ocr_text,
                "browser_url": context_data.browser_url,
                "timestamp": context_data.timestamp.isoformat()
            }
        }))
    
    elif message_type == "overlay_action":
        # Handle overlay toggle requests
        action = message.get("action")
        if action == "toggle_ai_assist":
            result = await horizon_app.overlay_manager.toggle_ai_assist()
            await websocket.send_text(json.dumps({
                "type": "overlay_response",
                "data": result
            }))
        elif action == "toggle_auto_context":
            result = await horizon_app.overlay_manager.toggle_auto_context()
            await websocket.send_text(json.dumps({
                "type": "overlay_response", 
                "data": result
            }))
        elif action == "toggle_quick_capture":
            result = await horizon_app.overlay_manager.toggle_quick_capture()
            await websocket.send_text(json.dumps({
                "type": "overlay_response",
                "data": result
            }))
    
    elif message_type == "ai_message":
        # Send message to AI
        text = message.get("text", "")
        smarter_analysis = message.get("smarter_analysis", False)
        
        if text:
            await horizon_app.send_ai_message(text, smarter_analysis)
            await websocket.send_text(json.dumps({
                "type": "ai_message_sent",
                "status": "success"
            }))
    
    elif message_type == "search_context":
        # Search for context notes
        ocr_text = message.get("ocr_text", "")
        
        if ocr_text:
            if not horizon_app.auto_context_manager.context_search_api.is_connected:
                await horizon_app.auto_context_manager.connect()
            
            await horizon_app.auto_context_manager.search_context(ocr_text)
            await websocket.send_text(json.dumps({
                "type": "context_search_started",
                "status": "success"
            }))


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "Horizon AI Assistant Backend is running",
        "components": {
            "ai_connected": horizon_app.ai_connection_manager.is_connected,
            "auth_status": horizon_app.auth_manager.is_authenticated,
            "tag_manager_connected": horizon_app.tag_websocket_manager.is_connected,
            "context_search_connected": horizon_app.auto_context_manager.context_search_api.is_connected
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )