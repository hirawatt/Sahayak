"""
Global hotkey management using evdev for Linux
"""

import asyncio
import logging
from typing import Dict, Callable, List, Optional
from pathlib import Path
import evdev
from evdev import InputDevice, categorize, ecodes
from threading import Thread
from dataclasses import dataclass

from config.settings import HotkeyConfig


@dataclass
class KeyCombo:
    """Represents a key combination"""
    modifiers: List[str]
    key: str
    
    @classmethod
    def from_string(cls, combo_str: str) -> 'KeyCombo':
        """Parse hotkey string like 'ctrl+shift+space'"""
        parts = combo_str.lower().split('+')
        key = parts[-1]
        modifiers = parts[:-1]
        return cls(modifiers=modifiers, key=key)


class HotkeyManager:
    """Manages global hotkeys using evdev"""
    
    def __init__(self, hotkey_config: HotkeyConfig):
        self.config = hotkey_config
        self.logger = logging.getLogger(__name__)
        
        # Device management
        self.devices: List[InputDevice] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Key state tracking
        self.pressed_keys: set = set()
        self.pressed_modifiers: set = set()
        
        # Callback management
        self.callbacks: Dict[str, Callable] = {}
        
        # Key mappings
        self.modifier_map = {
            'ctrl': [ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL],
            'shift': [ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT],
            'alt': [ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT],
            'super': [ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA],
            'cmd': [ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA],  # Alias for super
        }
        
        self.key_map = {
            'space': ecodes.KEY_SPACE,
            'enter': ecodes.KEY_ENTER,
            'return': ecodes.KEY_ENTER,
            'tab': ecodes.KEY_TAB,
            'escape': ecodes.KEY_ESC,
            'esc': ecodes.KEY_ESC,
            'comma': ecodes.KEY_COMMA,
            'period': ecodes.KEY_DOT,
            'slash': ecodes.KEY_SLASH,
            'backslash': ecodes.KEY_BACKSLASH,
            'minus': ecodes.KEY_MINUS,
            'equal': ecodes.KEY_EQUAL,
            'semicolon': ecodes.KEY_SEMICOLON,
            'apostrophe': ecodes.KEY_APOSTROPHE,
            'grave': ecodes.KEY_GRAVE,
            'leftbracket': ecodes.KEY_LEFTBRACE,
            'rightbracket': ecodes.KEY_RIGHTBRACE,
        }
        
        # Add letter and number keys
        for i in range(26):
            letter = chr(ord('a') + i)
            self.key_map[letter] = getattr(ecodes, f'KEY_{letter.upper()}')
        
        for i in range(10):
            self.key_map[str(i)] = getattr(ecodes, f'KEY_{i}')
        
        # Function keys
        for i in range(1, 13):
            self.key_map[f'f{i}'] = getattr(ecodes, f'KEY_F{i}')
        
        # Parse hotkey combinations
        self.hotkey_combos = {
            'ai_assist': KeyCombo.from_string(hotkey_config.ai_assist),
            'quick_capture': KeyCombo.from_string(hotkey_config.quick_capture),
            'auto_context': KeyCombo.from_string(hotkey_config.auto_context),
            'toggle_settings': KeyCombo.from_string(hotkey_config.toggle_settings),
        }
    
    async def start(self):
        """Start monitoring keyboard input"""
        self.logger.info("Starting hotkey manager")
        
        try:
            # Find keyboard devices
            await self._find_keyboard_devices()
            
            if not self.devices:
                self.logger.error("No keyboard devices found")
                return
            
            # Start monitoring in background task
            self.monitoring_task = asyncio.create_task(self._monitor_devices())
            self.logger.info(f"Monitoring {len(self.devices)} keyboard devices")
            
        except Exception as e:
            self.logger.error(f"Failed to start hotkey manager: {e}")
            raise
    
    async def stop(self):
        """Stop monitoring keyboard input"""
        self.logger.info("Stopping hotkey manager")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close devices
        for device in self.devices:
            device.close()
        self.devices.clear()
    
    async def _find_keyboard_devices(self):
        """Find available keyboard input devices"""
        self.devices.clear()
        
        # Look for devices in /dev/input/
        input_dir = Path('/dev/input')
        if not input_dir.exists():
            return
        
        for device_path in input_dir.glob('event*'):
            try:
                device = InputDevice(str(device_path))
                
                # Check if device has keyboard capabilities
                capabilities = device.capabilities()
                if ecodes.EV_KEY in capabilities:
                    # Check for common keyboard keys
                    keys = capabilities[ecodes.EV_KEY]
                    if any(key in keys for key in [ecodes.KEY_SPACE, ecodes.KEY_ENTER, ecodes.KEY_A]):
                        self.devices.append(device)
                        self.logger.debug(f"Found keyboard device: {device.name} ({device_path})")
                
            except (OSError, PermissionError) as e:
                self.logger.debug(f"Cannot access {device_path}: {e}")
                continue
    
    async def _monitor_devices(self):
        """Monitor all keyboard devices for input"""
        while True:
            try:
                # Wait for input from any device
                for device in self.devices:
                    try:
                        # Non-blocking read
                        events = device.read()
                        if events:
                            for event in events:
                                await self._process_event(event)
                    except BlockingIOError:
                        # No events available
                        continue
                    except OSError:
                        # Device disconnected
                        self.logger.warning(f"Device {device.name} disconnected")
                        continue
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring devices: {e}")
                await asyncio.sleep(1)
    
    async def _process_event(self, event):
        """Process a keyboard event"""
        if event.type != ecodes.EV_KEY:
            return
        
        key_event = categorize(event)
        
        # Track key state
        if key_event.keystate == key_event.key_down:
            self._handle_key_down(event.code)
        elif key_event.keystate == key_event.key_up:
            self._handle_key_up(event.code)
    
    def _handle_key_down(self, keycode):
        """Handle key press"""
        self.pressed_keys.add(keycode)
        
        # Check if it's a modifier
        for modifier, codes in self.modifier_map.items():
            if keycode in codes:
                self.pressed_modifiers.add(modifier)
                return
        
        # Check for hotkey matches
        self._check_hotkey_match()
    
    def _handle_key_up(self, keycode):
        """Handle key release"""
        self.pressed_keys.discard(keycode)
        
        # Check if it's a modifier
        for modifier, codes in self.modifier_map.items():
            if keycode in codes:
                self.pressed_modifiers.discard(modifier)
                return
    
    def _check_hotkey_match(self):
        """Check if current key combination matches any hotkey"""
        for action, combo in self.hotkey_combos.items():
            if self._is_combo_pressed(combo):
                self.logger.debug(f"Hotkey triggered: {action}")
                asyncio.create_task(self._trigger_callback(action))
    
    def _is_combo_pressed(self, combo: KeyCombo) -> bool:
        """Check if a key combination is currently pressed"""
        # Check modifiers
        for modifier in combo.modifiers:
            if modifier not in self.pressed_modifiers:
                return False
        
        # Check main key
        if combo.key in self.key_map:
            target_keycode = self.key_map[combo.key]
            if target_keycode not in self.pressed_keys:
                return False
        else:
            return False
        
        # Ensure no extra modifiers are pressed
        if len(self.pressed_modifiers) != len(combo.modifiers):
            return False
        
        return True
    
    async def _trigger_callback(self, action: str):
        """Trigger callback for action"""
        if action in self.callbacks:
            try:
                callback = self.callbacks[action]
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error in hotkey callback for {action}: {e}")
    
    def register_callback(self, action: str, callback: Callable):
        """Register a callback for an action"""
        self.callbacks[action] = callback
        self.logger.debug(f"Registered callback for action: {action}")
    
    def unregister_callback(self, action: str):
        """Unregister a callback for an action"""
        if action in self.callbacks:
            del self.callbacks[action]
            self.logger.debug(f"Unregistered callback for action: {action}")
    
    def update_hotkeys(self, new_config: HotkeyConfig):
        """Update hotkey configuration"""
        self.config = new_config
        self.hotkey_combos = {
            'ai_assist': KeyCombo.from_string(new_config.ai_assist),
            'quick_capture': KeyCombo.from_string(new_config.quick_capture),
            'auto_context': KeyCombo.from_string(new_config.auto_context),
            'toggle_settings': KeyCombo.from_string(new_config.toggle_settings),
        }
        self.logger.info("Hotkey configuration updated")