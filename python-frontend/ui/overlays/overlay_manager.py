"""
Overlay management system for Horizon Frontend
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import Settings
from ui.windows.ai_assist_window import AIAssistWindow
from ui.windows.quick_capture_window import QuickCaptureWindow
from ui.windows.auto_context_window import AutoContextWindow


class OverlayManager(QObject):
    """Manages all overlay windows"""
    
    # Signals
    overlay_toggled = pyqtSignal(str, bool)  # overlay_name, is_visible
    
    def __init__(self, settings: Settings, backend_client=None):
        super().__init__()
        self.settings = settings
        self.backend_client = backend_client
        self.logger = logging.getLogger(__name__)
        
        # Overlay windows
        self.ai_assist_window: Optional[AIAssistWindow] = None
        self.quick_capture_window: Optional[QuickCaptureWindow] = None
        self.auto_context_window: Optional[AutoContextWindow] = None
        
        # State tracking
        self.overlay_states = {
            'ai_assist': False,
            'quick_capture': False,
            'auto_context': False
        }
    
    async def initialize(self):
        """Initialize overlay windows"""
        self.logger.info("Initializing overlay windows")
        
        # Create overlay windows
        self.ai_assist_window = AIAssistWindow(self.settings, self.backend_client)
        self.quick_capture_window = QuickCaptureWindow(self.settings, self.backend_client)
        self.auto_context_window = AutoContextWindow(self.settings, self.backend_client)
        
        # Connect signals
        self.ai_assist_window.window_closed.connect(lambda: self._on_overlay_closed('ai_assist'))
        self.quick_capture_window.window_closed.connect(lambda: self._on_overlay_closed('quick_capture'))
        self.auto_context_window.window_closed.connect(lambda: self._on_overlay_closed('auto_context'))
    
    async def toggle_ai_assist(self) -> Dict[str, Any]:
        """Toggle AI Assist overlay"""
        if not self.ai_assist_window:
            await self.initialize()
        
        is_visible = self.ai_assist_window.isVisible()
        
        if is_visible:
            self.ai_assist_window.hide()
            self.overlay_states['ai_assist'] = False
        else:
            self.ai_assist_window.show()
            self.ai_assist_window.raise_()
            self.ai_assist_window.activateWindow()
            self.overlay_states['ai_assist'] = True
        
        new_state = not is_visible
        self.overlay_toggled.emit('ai_assist', new_state)
        
        return {'state': new_state, 'overlay': 'ai_assist'}
    
    async def toggle_quick_capture(self) -> Dict[str, Any]:
        """Toggle Quick Capture overlay"""
        if not self.quick_capture_window:
            await self.initialize()
        
        is_visible = self.quick_capture_window.isVisible()
        
        if is_visible:
            self.quick_capture_window.hide()
            self.overlay_states['quick_capture'] = False
        else:
            self.quick_capture_window.show()
            self.quick_capture_window.raise_()
            self.quick_capture_window.activateWindow()
            self.overlay_states['quick_capture'] = True
        
        new_state = not is_visible
        self.overlay_toggled.emit('quick_capture', new_state)
        
        return {'state': new_state, 'overlay': 'quick_capture'}
    
    async def toggle_auto_context(self) -> Dict[str, Any]:
        """Toggle Auto Context overlay"""
        if not self.auto_context_window:
            await self.initialize()
        
        is_visible = self.auto_context_window.isVisible()
        
        if is_visible:
            self.auto_context_window.hide()
            self.overlay_states['auto_context'] = False
        else:
            self.auto_context_window.show()
            self.auto_context_window.raise_()
            self.auto_context_window.activateWindow()
            self.overlay_states['auto_context'] = True
        
        new_state = not is_visible
        self.overlay_toggled.emit('auto_context', new_state)
        
        return {'state': new_state, 'overlay': 'auto_context'}
    
    def hide_all(self):
        """Hide all overlay windows"""
        if self.ai_assist_window:
            self.ai_assist_window.hide()
        if self.quick_capture_window:
            self.quick_capture_window.hide()
        if self.auto_context_window:
            self.auto_context_window.hide()
        
        self.overlay_states = {key: False for key in self.overlay_states}
    
    def get_overlay_state(self, overlay_name: str) -> bool:
        """Get overlay visibility state"""
        return self.overlay_states.get(overlay_name, False)
    
    def _on_overlay_closed(self, overlay_name: str):
        """Handle overlay window closed"""
        self.overlay_states[overlay_name] = False
        self.overlay_toggled.emit(overlay_name, False)
        self.logger.debug(f"Overlay {overlay_name} closed")