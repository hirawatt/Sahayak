"""
Main Overlay Manager - Coordinates all overlay windows
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

from ui.windows.ai_assist_window import AIAssistWindow
from ui.windows.quick_capture_window import QuickCaptureWindow
from ui.windows.auto_context_window import AutoContextWindow
from config.settings import Settings
from services.backend_client import BackendClient
from services.shortcut_manager import ShortcutManager


class OverlayManager(QObject):
    """Main overlay manager - coordinates all overlay windows"""
    
    # Signals
    overlay_shown = pyqtSignal(str)  # overlay_type
    overlay_hidden = pyqtSignal(str)  # overlay_type
    context_changed = pyqtSignal(dict)  # context_data
    
    def __init__(self, settings: Settings, backend_client: Optional[BackendClient] = None):
        super().__init__()
        self.settings = settings
        self.backend_client = backend_client
        self.logger = logging.getLogger(__name__)
        
        # Window instances
        self.ai_assist_window: Optional[AIAssistWindow] = None
        self.quick_capture_window: Optional[QuickCaptureWindow] = None
        self.auto_context_window: Optional[AutoContextWindow] = None
        
        # State
        self.active_overlays: Set[str] = set()
        self.current_context: Dict[str, Any] = {}
        self.selected_text: str = ""
        
        # Services
        self.shortcut_manager: Optional[ShortcutManager] = None
        
        # Initialize
        self._setup_shortcuts()
        self._connect_backend()
        
        # Context monitoring timer
        self.context_timer = QTimer()
        self.context_timer.timeout.connect(self._monitor_context)
        self.context_timer.start(1000)  # Check every second
    
    def _setup_shortcuts(self):
        """Setup global shortcuts for overlays"""
        try:
            self.shortcut_manager = ShortcutManager(self.settings)
            
            # Register shortcuts
            self.shortcut_manager.register_shortcut(
                "ai_assist", 
                self.settings.hotkeys.ai_assist,
                self.toggle_ai_assist
            )
            
            self.shortcut_manager.register_shortcut(
                "quick_capture",
                self.settings.hotkeys.quick_capture,
                self.toggle_quick_capture
            )
            
            self.shortcut_manager.register_shortcut(
                "auto_context",
                self.settings.hotkeys.auto_context,
                self.toggle_auto_context
            )
            
            self.logger.info("Global shortcuts registered successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup shortcuts: {e}")
    
    def _connect_backend(self):
        """Connect to backend for real-time updates"""
        if self.backend_client:
            self.backend_client.register_message_handler('context_changed', self._on_context_changed)
            self.backend_client.register_message_handler('selected_text', self._on_selected_text_changed)
            self.backend_client.register_message_handler('window_focus', self._on_window_focus_changed)
    
    def _monitor_context(self):
        """Monitor system context periodically"""
        if self.backend_client:
            # Use QTimer to periodically update context
            from PyQt6.QtCore import QTimer
            self.context_timer = QTimer()
            self.context_timer.timeout.connect(self._schedule_context_update)
            self.context_timer.start(5000)  # Update every 5 seconds
    
    def _schedule_context_update(self):
        """Schedule context update in the event loop"""
        if self.backend_client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._update_context())
            except RuntimeError:
                # No event loop running, skip this update
                pass
    
    async def _update_context(self):
        """Update current context from system"""
        try:
            response = await self.backend_client.capture_context()
            if response.success:
                new_context = response.data
                if new_context != self.current_context:
                    self.current_context = new_context
                    self.context_changed.emit(new_context)
                    self._propagate_context_updates()
        except Exception as e:
            self.logger.debug(f"Context update failed: {e}")
    
    def _propagate_context_updates(self):
        """Propagate context updates to active overlays"""
        # Update AI Assist with selected text
        if self.ai_assist_window and "ai_assist" in self.active_overlays:
            selected_text = self.current_context.get('selected_text', '')
            if selected_text != self.selected_text:
                self.selected_text = selected_text
                self.ai_assist_window.update_selected_text(selected_text)
        
        # Update Auto Context if it's visible
        if self.auto_context_window and "auto_context" in self.active_overlays:
            # Auto context will refresh itself based on context changes
            pass
    
    # AI Assist Window Management
    def show_ai_assist(self, selected_text: str = ""):
        """Show AI Assist window"""
        if not self.ai_assist_window:
            self.ai_assist_window = AIAssistWindow(self.settings, self.backend_client)
            self.ai_assist_window.window_closed.connect(lambda: self._on_overlay_closed("ai_assist"))
            self.ai_assist_window.message_sent.connect(self._on_ai_message_sent)
        
        if selected_text:
            self.ai_assist_window.update_selected_text(selected_text)
        
        self.ai_assist_window.show()
        self.active_overlays.add("ai_assist")
        self.overlay_shown.emit("ai_assist")
        self.logger.info("AI Assist window shown")
    
    def hide_ai_assist(self):
        """Hide AI Assist window"""
        if self.ai_assist_window:
            self.ai_assist_window.hide()
            self.active_overlays.discard("ai_assist")
            self.overlay_hidden.emit("ai_assist")
    
    def toggle_ai_assist(self):
        """Toggle AI Assist window"""
        if "ai_assist" in self.active_overlays:
            self.hide_ai_assist()
        else:
            selected_text = self.current_context.get('selected_text', '')
            self.show_ai_assist(selected_text)
    
    # Quick Capture Window Management
    def show_quick_capture(self):
        """Show Quick Capture window"""
        if not self.quick_capture_window:
            self.quick_capture_window = QuickCaptureWindow(self.settings, self.backend_client)
            self.quick_capture_window.window_closed.connect(lambda: self._on_overlay_closed("quick_capture"))
            self.quick_capture_window.capture_saved.connect(self._on_capture_saved)
        
        self.quick_capture_window.show()
        self.active_overlays.add("quick_capture")
        self.overlay_shown.emit("quick_capture")
        self.logger.info("Quick Capture window shown")
    
    def hide_quick_capture(self):
        """Hide Quick Capture window"""
        if self.quick_capture_window:
            self.quick_capture_window.hide()
            self.active_overlays.discard("quick_capture")
            self.overlay_hidden.emit("quick_capture")
    
    def toggle_quick_capture(self):
        """Toggle Quick Capture window"""
        if "quick_capture" in self.active_overlays:
            self.hide_quick_capture()
        else:
            self.show_quick_capture()
    
    # Auto Context Window Management
    def show_auto_context(self):
        """Show Auto Context window"""
        if not self.auto_context_window:
            self.auto_context_window = AutoContextWindow(self.settings, self.backend_client)
            self.auto_context_window.window_closed.connect(lambda: self._on_overlay_closed("auto_context"))
            self.auto_context_window.context_selected.connect(self._on_context_selected)
            self.auto_context_window.search_requested.connect(self._on_context_search)
        
        self.auto_context_window.show()
        self.active_overlays.add("auto_context")
        self.overlay_shown.emit("auto_context")
        self.logger.info("Auto Context window shown")
    
    def hide_auto_context(self):
        """Hide Auto Context window"""
        if self.auto_context_window:
            self.auto_context_window.hide()
            self.active_overlays.discard("auto_context")
            self.overlay_hidden.emit("auto_context")
    
    def toggle_auto_context(self):
        """Toggle Auto Context window"""
        if "auto_context" in self.active_overlays:
            self.hide_auto_context()
        else:
            self.show_auto_context()
    
    # Utility Methods
    def hide_all_overlays(self):
        """Hide all overlay windows"""
        self.hide_ai_assist()
        self.hide_quick_capture()
        self.hide_auto_context()
    
    def get_active_overlays(self) -> Set[str]:
        """Get set of currently active overlay types"""
        return self.active_overlays.copy()
    
    def is_overlay_active(self, overlay_type: str) -> bool:
        """Check if an overlay is currently active"""
        return overlay_type in self.active_overlays
    
    # Event Handlers
    def _on_overlay_closed(self, overlay_type: str):
        """Handle overlay window close"""
        self.active_overlays.discard(overlay_type)
        self.overlay_hidden.emit(overlay_type)
        self.logger.debug(f"{overlay_type} overlay closed")
    
    def _on_ai_message_sent(self, message: str):
        """Handle AI message sent"""
        self.logger.debug(f"AI message sent: {message[:50]}...")
        
        # Optionally show context window if AI conversation starts
        if self.settings.ui.auto_show_context and not self.is_overlay_active("auto_context"):
            self.show_auto_context()
    
    def _on_capture_saved(self, capture_text: str):
        """Handle capture saved"""
        self.logger.info(f"Capture saved: {len(capture_text)} characters")
        
        # Optionally refresh context after capture
        if self.auto_context_window and "auto_context" in self.active_overlays:
            self.auto_context_window._refresh_context()
    
    def _on_context_selected(self, context_data: Dict[str, Any]):
        """Handle context item selection"""
        self.logger.debug(f"Context selected: {context_data.get('title', 'Unknown')}")
        
        # Optionally open AI Assist with context
        if self.settings.ui.auto_open_ai_with_context:
            if not self.is_overlay_active("ai_assist"):
                self.show_ai_assist()
            
            # Set the context in AI Assist
            if self.ai_assist_window:
                content = context_data.get('content', '')
                if content:
                    self.ai_assist_window.update_selected_text(content[:500] + "..." if len(content) > 500 else content)
    
    def _on_context_search(self, query: str):
        """Handle context search request"""
        self.logger.debug(f"Context search: {query}")
    
    # Backend Event Handlers
    def _on_context_changed(self, data: Dict[str, Any]):
        """Handle context change from backend"""
        self.current_context.update(data)
        self.context_changed.emit(self.current_context)
        self._propagate_context_updates()
    
    def _on_selected_text_changed(self, data: Dict[str, Any]):
        """Handle selected text change"""
        selected_text = data.get('text', '')
        if selected_text != self.selected_text:
            self.selected_text = selected_text
            self.current_context['selected_text'] = selected_text
            
            # Update AI Assist if active
            if self.ai_assist_window and "ai_assist" in self.active_overlays:
                self.ai_assist_window.update_selected_text(selected_text)
    
    def _on_window_focus_changed(self, data: Dict[str, Any]):
        """Handle window focus changes"""
        window_title = data.get('window_title', '')
        app_name = data.get('app_name', '')
        
        self.current_context.update({
            'active_window': window_title,
            'active_app': app_name
        })
        
        self.logger.debug(f"Window focus changed: {app_name} - {window_title}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.context_timer.stop()
        
        if self.shortcut_manager:
            self.shortcut_manager.cleanup()
        
        self.hide_all_overlays()
        
        # Clean up window instances
        if self.ai_assist_window:
            self.ai_assist_window.deleteLater()
            self.ai_assist_window = None
        
        if self.quick_capture_window:
            self.quick_capture_window.deleteLater()
            self.quick_capture_window = None
        
        if self.auto_context_window:
            self.auto_context_window.deleteLater()
            self.auto_context_window = None
        
        self.logger.info("Overlay manager cleaned up")