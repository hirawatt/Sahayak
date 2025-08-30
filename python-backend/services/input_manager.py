"""
Input Event Manager - Python equivalent of InputEventManager.swift
Handles global hotkeys (cross-platform)
"""

import asyncio
import sys
from typing import Dict, Callable, Optional, List
import threading
from dataclasses import dataclass

# Platform-specific imports
if sys.platform == "darwin":
    try:
        import pynput
        from pynput import keyboard
        PYNPUT_AVAILABLE = True
    except ImportError:
        PYNPUT_AVAILABLE = False
        print("pynput not available - hotkeys disabled")
else:
    try:
        import evdev
        from evdev import InputDevice, categorize, ecodes
        EVDEV_AVAILABLE = True
    except ImportError:
        EVDEV_AVAILABLE = False
        try:
            import pynput
            from pynput import keyboard
            PYNPUT_AVAILABLE = True
        except ImportError:
            PYNPUT_AVAILABLE = False
            print("Neither evdev nor pynput available - hotkeys disabled")

from models.shortcut import Shortcut


@dataclass
class HotkeyEvent:
    """Represents a hotkey event"""
    shortcut: Shortcut
    action: str  # "aiAssist", "autoContext", "quickCapture"


class InputManager:
    """Manages global hotkey detection (cross-platform)"""
    
    def __init__(self):
        self.running = False
        self.hotkey_callbacks: Dict[str, Callable] = {}
        self.available = PYNPUT_AVAILABLE or (sys.platform != "darwin" and EVDEV_AVAILABLE)
        
        # Default shortcuts matching Swift app
        self.shortcuts = {
            'aiAssist': Shortcut(key='1', modifiers=['super', 'shift']),  # Super+Shift+1
            'autoContext': Shortcut(key='o', modifiers=['super', 'shift']),  # Super+Shift+O  
            'quickCapture': Shortcut(key='2', modifiers=['super', 'shift'])  # Super+Shift+2
        }
        
        self.hotkey_manager = None
        self.listener = None
    
    async def setup(self):
        """Initialize input device monitoring"""
        if not self.available:
            print("Input monitoring not available on this platform")
            return
        
        if sys.platform == "darwin" and PYNPUT_AVAILABLE:
            await self._setup_pynput()
        else:
            print("Hotkey monitoring not implemented for this platform yet")
    
    async def _setup_pynput(self):
        """Setup pynput-based hotkey monitoring for macOS"""
        try:
            # Create hotkey combinations
            hotkeys = {}
            
            for action, shortcut in self.shortcuts.items():
                # Convert shortcut to pynput format
                key_combo = self._shortcut_to_pynput(shortcut)
                if key_combo:
                    hotkeys[key_combo] = lambda action=action: asyncio.create_task(
                        self._trigger_hotkey(action)
                    )
            
            if hotkeys:
                # Start global hotkey listener
                self.listener = keyboard.GlobalHotKeys(hotkeys)
                self.listener.start()
                self.running = True
                print(f"Hotkey monitoring started with {len(hotkeys)} shortcuts")
            
        except Exception as e:
            print(f"Failed to setup hotkey monitoring: {e}")
    
    def _shortcut_to_pynput(self, shortcut: Shortcut) -> Optional[frozenset]:
        """Convert Shortcut to pynput hotkey format"""
        try:
            keys = set()
            
            # Add modifiers
            for modifier in shortcut.modifiers:
                if modifier == 'super':
                    keys.add(keyboard.Key.cmd)
                elif modifier == 'ctrl':
                    keys.add(keyboard.Key.ctrl)
                elif modifier == 'shift':
                    keys.add(keyboard.Key.shift)
                elif modifier == 'alt':
                    keys.add(keyboard.Key.alt)
            
            # Add main key
            if len(shortcut.key) == 1:
                keys.add(keyboard.KeyCode.from_char(shortcut.key.lower()))
            else:
                # Handle special keys
                special_keys = {
                    'space': keyboard.Key.space,
                    'enter': keyboard.Key.enter,
                    'tab': keyboard.Key.tab,
                    'escape': keyboard.Key.esc,
                }
                if shortcut.key.lower() in special_keys:
                    keys.add(special_keys[shortcut.key.lower()])
                else:
                    return None
            
            return frozenset(keys)
            
        except Exception as e:
            print(f"Error converting shortcut {shortcut}: {e}")
            return None
    
    async def _trigger_hotkey(self, action: str):
        """Trigger hotkey callback"""
        try:
            if action in self.hotkey_callbacks:
                callback = self.hotkey_callbacks[action]
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
        except Exception as e:
            print(f"Error triggering hotkey {action}: {e}")
    
    def register_hotkey_callback(self, action: str, callback: Callable):
        """Register callback for hotkey action"""
        self.hotkey_callbacks[action] = callback
        print(f"Registered hotkey callback for {action}")
    
    def unregister_hotkey_callback(self, action: str):
        """Unregister hotkey callback"""
        if action in self.hotkey_callbacks:
            del self.hotkey_callbacks[action]
    
    async def cleanup(self):
        """Clean up input monitoring"""
        try:
            self.running = False
            
            if self.listener:
                self.listener.stop()
                self.listener = None
            
            print("Input manager cleaned up")
            
        except Exception as e:
            print(f"Error cleaning up input manager: {e}")