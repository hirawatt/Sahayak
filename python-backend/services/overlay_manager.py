"""
Overlay Manager - Python equivalent for managing overlay state
Coordinates with PyQt6 frontend for overlay display
"""

import asyncio
from typing import Dict, Any, Optional
from services.context_manager import AIContextManager


class OverlayManager:
    """Manages overlay states and coordinates with PyQt6 frontend"""
    
    def __init__(self):
        self.context_manager = AIContextManager()
        self.overlay_states = {
            'aiAssist': False,
            'autoContext': False,
            'quickCapture': False
        }
        self.websocket_connections = []
    
    async def setup(self):
        """Initialize overlay manager"""
        print("Overlay Manager initialized")
    
    async def cleanup(self):
        """Cleanup overlay manager"""
        print("Overlay Manager cleaned up")
    
    async def toggle_ai_assist(self) -> Dict[str, Any]:
        """Toggle AI Assist overlay - equivalent to AIAssistOverlayManager.toggle()"""
        current_state = self.overlay_states['aiAssist']
        new_state = not current_state
        
        if new_state:
            # Capture context when showing overlay
            context_data = await self.context_manager.capture_current_context(capture_image=True)
            
            result = {
                'action': 'show_ai_assist',
                'state': True,
                'context': {
                    'selected_text': context_data.selected_text,
                    'ocr_text': context_data.ocr_text,
                    'browser_url': context_data.browser_url,
                    'has_image': context_data.image_data is not None
                }
            }
        else:
            result = {
                'action': 'hide_ai_assist',
                'state': False
            }
        
        self.overlay_states['aiAssist'] = new_state
        
        # Notify connected PyQt6 frontend via WebSocket
        await self._broadcast_to_frontend(result)
        
        return result
    
    async def toggle_auto_context(self) -> Dict[str, Any]:
        """Toggle Auto Context overlay - equivalent to AutoContextOverlay.toggle()"""
        current_state = self.overlay_states['autoContext']
        new_state = not current_state
        
        if new_state:
            # Capture context for auto context
            context_data = await self.context_manager.capture_current_context(capture_image=False)
            
            result = {
                'action': 'show_auto_context',
                'state': True,
                'context': {
                    'selected_text': context_data.selected_text,
                    'ocr_text': context_data.ocr_text,
                    'browser_url': context_data.browser_url
                }
            }
        else:
            result = {
                'action': 'hide_auto_context',
                'state': False
            }
        
        self.overlay_states['autoContext'] = new_state
        await self._broadcast_to_frontend(result)
        
        return result
    
    async def toggle_quick_capture(self) -> Dict[str, Any]:
        """Toggle Quick Capture overlay - equivalent to QuickCaptureOverlay.toggle()"""
        current_state = self.overlay_states['quickCapture']
        new_state = not current_state
        
        result = {
            'action': 'show_quick_capture' if new_state else 'hide_quick_capture',
            'state': new_state
        }
        
        self.overlay_states['quickCapture'] = new_state
        await self._broadcast_to_frontend(result)
        
        return result
    
    async def _broadcast_to_frontend(self, message: Dict[str, Any]):
        """Broadcast message to all connected PyQt6 frontend instances"""
        # This will be implemented when WebSocket connections are established
        print(f"Broadcasting to frontend: {message}")
    
    def add_websocket_connection(self, websocket):
        """Add WebSocket connection for frontend communication"""
        self.websocket_connections.append(websocket)
    
    def remove_websocket_connection(self, websocket):
        """Remove WebSocket connection"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)