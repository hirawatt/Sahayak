"""
Input Event Handler for Horizon Overlay.
Coordinates hotkey and voice input events and routes them to appropriate handlers.
"""

import asyncio
from typing import Dict, Callable, Optional, Any
from .hotkey_manager import HotkeyManager
from .voice_input_manager import VoiceInputManager
from .shortcut_config import ShortcutConfig

class InputEventHandler:
    """Central coordinator for all input events (keyboard and voice)."""
    
    def __init__(self):
        self.shortcut_config = ShortcutConfig()
        self.hotkey_manager = HotkeyManager(self.shortcut_config)
        self.voice_manager = VoiceInputManager()
        
        self.overlay_callbacks: Dict[str, Callable] = {}
        self.running = False
        
        # Setup default event handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default event handlers for overlay actions."""
        # Register voice callbacks
        self.voice_manager.register_callback('voice_start', self._on_voice_start)
        self.voice_manager.register_callback('voice_end', self._on_voice_end)
        self.voice_manager.register_callback('audio_recorded', self._on_audio_recorded)
        
        # Register default shortcut callbacks
        self.register_overlay_callback('ai_assist', self._show_ai_assist)
        self.register_overlay_callback('quick_capture', self._show_quick_capture)
        self.register_overlay_callback('auto_context', self._show_auto_context)
        self.register_overlay_callback('voice_activate', self._toggle_voice_recording)
        self.register_overlay_callback('close_overlay', self._close_current_overlay)
    
    async def start(self) -> bool:
        """Start all input event monitoring."""
        if self.running:
            return True
        
        success = True
        
        # Start hotkey monitoring
        hotkey_started = await self.hotkey_manager.start()
        if not hotkey_started:
            print("Warning: Hotkey monitoring failed to start")
            success = False
        
        # Start voice monitoring
        voice_started = self.voice_manager.start_listening()
        if not voice_started:
            print("Warning: Voice monitoring failed to start")
            success = False
        
        if success:
            self.running = True
            print("Input event handler started successfully")
        else:
            print("Input event handler started with some failures")
        
        return success
    
    def stop(self):
        """Stop all input event monitoring."""
        if not self.running:
            return
        
        self.hotkey_manager.stop()
        self.voice_manager.stop_listening()
        self.running = False
        print("Input event handler stopped")
    
    def register_overlay_callback(self, action: str, callback: Callable):
        """Register a callback for overlay actions."""
        self.overlay_callbacks[action] = callback
        self.hotkey_manager.register_shortcut_callback(action, callback)
    
    def unregister_overlay_callback(self, action: str):
        """Unregister a callback for overlay actions."""
        if action in self.overlay_callbacks:
            del self.overlay_callbacks[action]
    
    # Default overlay action handlers (placeholders)
    def _show_ai_assist(self):
        """Show AI Assist overlay."""
        print("Action: Show AI Assist overlay")
        if 'ai_assist' in self.overlay_callbacks:
            try:
                self.overlay_callbacks['ai_assist']()
            except Exception as e:
                print(f"Error showing AI Assist: {e}")
    
    def _show_quick_capture(self):
        """Show Quick Capture overlay."""
        print("Action: Show Quick Capture overlay")
        if 'quick_capture' in self.overlay_callbacks:
            try:
                self.overlay_callbacks['quick_capture']()
            except Exception as e:
                print(f"Error showing Quick Capture: {e}")
    
    def _show_auto_context(self):
        """Show Auto Context overlay."""
        print("Action: Show Auto Context overlay")
        if 'auto_context' in self.overlay_callbacks:
            try:
                self.overlay_callbacks['auto_context']()
            except Exception as e:
                print(f"Error showing Auto Context: {e}")
    
    def _toggle_voice_recording(self):
        """Toggle voice recording."""
        if self.voice_manager.is_recording:
            audio_data = self.voice_manager.stop_recording()
            print("Voice recording stopped")
            if audio_data is not None:
                self._process_voice_input(audio_data)
        else:
            success = self.voice_manager.start_recording()
            if success:
                print("Voice recording started")
            else:
                print("Failed to start voice recording")
    
    def _close_current_overlay(self):
        """Close current overlay."""
        print("Action: Close current overlay")
        if 'close_overlay' in self.overlay_callbacks:
            try:
                self.overlay_callbacks['close_overlay']()
            except Exception as e:
                print(f"Error closing overlay: {e}")
    
    # Voice event handlers
    def _on_voice_start(self):
        """Handle voice activity start."""
        print("Voice activity detected")
    
    def _on_voice_end(self):
        """Handle voice activity end."""
        print("Voice activity ended")
    
    def _on_audio_recorded(self, data: Dict[str, Any]):
        """Handle recorded audio."""
        audio = data.get('audio')
        if audio is not None:
            print(f"Audio recorded: {len(audio)} samples")
            self._process_voice_input(audio)
    
    def _process_voice_input(self, audio_data):
        """Process voice input (placeholder for future STT integration)."""
        print("Processing voice input...")
        # TODO: Integrate speech-to-text processing
        # This would convert audio to text and potentially trigger AI responses
    
    # Configuration methods
    def add_shortcut(self, action: str, key: str, modifiers: list, 
                    callback: Optional[Callable] = None, description: str = ""):
        """Add a new keyboard shortcut."""
        try:
            self.hotkey_manager.add_shortcut(action, key, modifiers, callback, description)
            print(f"Shortcut added: {action} -> {'+'.join(modifiers + [key])}")
        except ValueError as e:
            print(f"Failed to add shortcut: {e}")
    
    def remove_shortcut(self, action: str):
        """Remove a keyboard shortcut."""
        self.hotkey_manager.remove_shortcut(action)
        print(f"Shortcut removed: {action}")
    
    def get_shortcuts(self):
        """Get all configured shortcuts."""
        return self.hotkey_manager.get_shortcuts()
    
    def set_voice_threshold(self, threshold: float):
        """Set voice activation threshold."""
        self.voice_manager.set_voice_threshold(threshold)
        print(f"Voice threshold set to: {threshold}")
    
    def test_voice_input(self, duration: float = 3.0):
        """Test voice input functionality."""
        return self.voice_manager.test_audio_input(duration)
    
    def get_audio_devices(self):
        """Get available audio input devices."""
        return self.voice_manager.list_audio_devices()
    
    def set_audio_device(self, device_id: Optional[int] = None):
        """Set the audio input device."""
        self.voice_manager.set_input_device(device_id)
        if device_id is not None:
            print(f"Audio device set to: {device_id}")
        else:
            print("Audio device set to default")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of input event handler."""
        return {
            'running': self.running,
            'hotkey_manager': {
                'running': self.hotkey_manager.running,
                'devices_count': len(self.hotkey_manager.devices)
            },
            'voice_manager': self.voice_manager.get_device_info(),
            'shortcuts_count': len(self.hotkey_manager.get_shortcuts()),
            'callbacks_count': len(self.overlay_callbacks)
        }