"""
D-Bus Interface for Horizon Overlay.
Handles D-Bus communication for system integration on Ubuntu/Wayland.
Cross-platform stub for macOS compatibility.
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional, Callable, List
import threading

# Platform-specific imports
if sys.platform != "darwin":
    try:
        import dbus
        import dbus.service
        from dbus.mainloop.glib import DBusGMainLoop
        import gi
        gi.require_version('GLib', '2.0')
        from gi.repository import GLib
        DBUS_AVAILABLE = True
    except ImportError:
        DBUS_AVAILABLE = False
        print("D-Bus not available - system integration limited")
else:
    DBUS_AVAILABLE = False
    # Create stub classes for macOS
    class dbus:
        class service:
            class Object:
                def __init__(self, bus, object_path):
                    pass
            
            @staticmethod
            def method(interface, in_signature='', out_signature=''):
                def decorator(func):
                    return func
                return decorator

class HorizonDBusService(dbus.service.Object if DBUS_AVAILABLE else object):
    """D-Bus service for Horizon AI Assistant."""
    
    def __init__(self, bus, object_path="/com/cluely/HorizonAI"):
        if DBUS_AVAILABLE:
            super().__init__(bus, object_path)
        self.callbacks: Dict[str, Callable] = {}
        self.status_data: Dict[str, Any] = {}
    
    if DBUS_AVAILABLE:
        @dbus.service.method("com.cluely.HorizonAI.Control",
                            in_signature='s', out_signature='b')
        def ToggleOverlay(self, overlay_name):
            """Toggle overlay via D-Bus."""
            try:
                if 'toggle_overlay' in self.callbacks:
                    result = self.callbacks['toggle_overlay'](overlay_name)
                    return bool(result)
                return False
            except Exception as e:
                print(f"D-Bus ToggleOverlay error: {e}")
                return False
        
        @dbus.service.method("com.cluely.HorizonAI.Control",
                            in_signature='ss', out_signature='b')
        def SendAIMessage(self, message, context):
            """Send message to AI via D-Bus."""
            try:
                if 'send_ai_message' in self.callbacks:
                    result = self.callbacks['send_ai_message'](message, context)
                    return bool(result)
                return False
            except Exception as e:
                print(f"D-Bus SendAIMessage error: {e}")
                return False
    else:
        # Stub methods for non-D-Bus platforms
        def ToggleOverlay(self, overlay_name):
            return False
        
        def SendAIMessage(self, message, context):
            return False
    
    def GetStatus(self):
        """Get application status via D-Bus."""
        try:
            return json.dumps(self.status_data)
        except Exception as e:
            print(f"D-Bus GetStatus error: {e}")
            return "{}"
    
    def CaptureContext(self):
        """Trigger context capture via D-Bus."""
        try:
            if 'capture_context' in self.callbacks:
                result = self.callbacks['capture_context']()
                return bool(result)
            return False
        except Exception as e:
            print(f"D-Bus CaptureContext error: {e}")
            return False
    
    def OverlayStateChanged(self, overlay_name, state):
        """Signal when overlay state changes."""
        pass
    
    def AIResponseReceived(self, response_preview):
        """Signal when AI response is received."""
        pass
    
    def ContextUpdated(self, context_summary):
        """Signal when context is updated."""
        pass
    
    def register_callback(self, method_name: str, callback: Callable):
        """Register callback for D-Bus method."""
        self.callbacks[method_name] = callback
    
    def update_status(self, status: Dict[str, Any]):
        """Update status data."""
        self.status_data.update(status)
    
    def emit_overlay_state_changed(self, overlay_name: str, state: bool):
        """Emit overlay state change signal."""
        self.OverlayStateChanged(overlay_name, state)
    
    def emit_ai_response_received(self, response: str):
        """Emit AI response signal."""
        preview = response[:100] + "..." if len(response) > 100 else response
        self.AIResponseReceived(preview)
    
    def emit_context_updated(self, context_summary: str):
        """Emit context update signal."""
        self.ContextUpdated(context_summary)

class DBusInterface:
    """D-Bus interface manager for system integration."""
    
    def __init__(self):
        self.service = None
        self.bus = None
        self.main_loop = None
        self.loop_thread = None
        self.is_running = False
        self.available = DBUS_AVAILABLE
        
        # External service connections
        self.gnome_shell = None
        self.notification_daemon = None
        
    async def setup(self) -> bool:
        """Setup D-Bus interface."""
        if not self.available:
            print("D-Bus not available on this platform - using stub implementation")
            self.is_running = True
            return True
            
        try:
            # Initialize D-Bus main loop
            DBusGMainLoop(set_as_default=True)
            
            # Connect to session bus
            self.bus = dbus.SessionBus()
            
            # Create our service
            bus_name = dbus.service.BusName("com.cluely.HorizonAI", self.bus)
            self.service = HorizonDBusService(self.bus)
            
            # Start GLib main loop in separate thread
            self.main_loop = GLib.MainLoop()
            self.loop_thread = threading.Thread(target=self._run_main_loop, daemon=True)
            self.loop_thread.start()
            
            # Connect to external services
            await self._connect_external_services()
            
            self.is_running = True
            print("D-Bus interface initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to setup D-Bus interface: {e}")
            return False
    
    def _run_main_loop(self):
        """Run GLib main loop in separate thread."""
        if not self.available:
            return
        try:
            self.main_loop.run()
        except Exception as e:
            print(f"D-Bus main loop error: {e}")
    
    async def _connect_external_services(self):
        """Connect to external D-Bus services."""
        if not self.available:
            return
        try:
            # Connect to GNOME Shell
            try:
                shell_proxy = self.bus.get_object('org.gnome.Shell', '/org/gnome/Shell')
                self.gnome_shell = dbus.Interface(shell_proxy, 'org.gnome.Shell')
                print("Connected to GNOME Shell D-Bus interface")
            except Exception as e:
                print(f"Could not connect to GNOME Shell: {e}")
            
            # Connect to notification daemon
            try:
                notify_proxy = self.bus.get_object('org.freedesktop.Notifications', 
                                                 '/org/freedesktop/Notifications')
                self.notification_daemon = dbus.Interface(notify_proxy, 
                                                        'org.freedesktop.Notifications')
                print("Connected to notification daemon")
            except Exception as e:
                print(f"Could not connect to notification daemon: {e}")
                
        except Exception as e:
            print(f"Error connecting to external services: {e}")
    
    def register_callback(self, method_name: str, callback: Callable):
        """Register callback for D-Bus method calls."""
        if self.service:
            self.service.register_callback(method_name, callback)
    
    def update_status(self, status: Dict[str, Any]):
        """Update application status for D-Bus clients."""
        if self.service:
            self.service.update_status(status)
    
    def emit_overlay_state_changed(self, overlay_name: str, state: bool):
        """Emit signal when overlay state changes."""
        if self.service:
            self.service.emit_overlay_state_changed(overlay_name, state)
    
    def emit_ai_response_received(self, response: str):
        """Emit signal when AI response is received."""
        if self.service:
            self.service.emit_ai_response_received(response)
    
    def emit_context_updated(self, context_summary: str):
        """Emit signal when context is updated."""
        if self.service:
            self.service.emit_context_updated(context_summary)
    
    async def cleanup(self):
        """Clean up D-Bus interface."""
        try:
            self.is_running = False
            
            if self.available and self.main_loop and hasattr(self.main_loop, 'is_running') and self.main_loop.is_running():
                self.main_loop.quit()
            
            if self.loop_thread and self.loop_thread.is_alive():
                self.loop_thread.join(timeout=2.0)
            
            self.service = None
            self.bus = None
            
            print("D-Bus interface cleaned up")
            
        except Exception as e:
            print(f"Error cleaning up D-Bus interface: {e}")