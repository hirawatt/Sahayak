"""
Global Hotkey Manager for Horizon Overlay using evdev.
Handles system-wide keyboard shortcut detection on Ubuntu/Wayland.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable, Set
import evdev
from evdev import InputDevice, categorize, ecodes
from .shortcut_config import ShortcutConfig, Shortcut

class HotkeyManager:
    """Manages global hotkeys using evdev for Wayland compatibility."""
    
    def __init__(self, shortcut_config: Optional[ShortcutConfig] = None):
        self.shortcut_config = shortcut_config or ShortcutConfig()
        self.devices: List[InputDevice] = []
        self.running = False
        self.monitor_thread = None
        self.pressed_keys: Set[int] = set()
        self.modifier_keys: Dict[str, int] = {
            'ctrl': ecodes.KEY_LEFTCTRL,
            'alt': ecodes.KEY_LEFTALT,
            'shift': ecodes.KEY_LEFTSHIFT,
            'super': ecodes.KEY_LEFTMETA
        }
        self.key_mapping: Dict[str, int] = self._build_key_mapping()
        
    def _build_key_mapping(self) -> Dict[str, int]:
        """Build mapping from key names to evdev key codes."""
        mapping = {}
        
        # Numbers
        for i in range(10):
            mapping[str(i)] = getattr(ecodes, f'KEY_{i}')
        
        # Letters
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            mapping[letter] = getattr(ecodes, f'KEY_{letter.upper()}')
        
        # Special keys
        special_keys = {
            'space': ecodes.KEY_SPACE,
            'enter': ecodes.KEY_ENTER,
            'escape': ecodes.KEY_ESC,
            'tab': ecodes.KEY_TAB,
            'backspace': ecodes.KEY_BACKSPACE,
            'delete': ecodes.KEY_DELETE,
            'up': ecodes.KEY_UP,
            'down': ecodes.KEY_DOWN,
            'left': ecodes.KEY_LEFT,
            'right': ecodes.KEY_RIGHT
        }
        
        # Function keys
        for i in range(1, 13):
            special_keys[f'f{i}'] = getattr(ecodes, f'KEY_F{i}')
        
        mapping.update(special_keys)
        return mapping
    
    def _find_keyboard_devices(self) -> List[InputDevice]:
        """Find all keyboard input devices."""
        devices = []
        for path in evdev.list_devices():
            try:
                device = InputDevice(path)
                # Check if device has keyboard capabilities
                if ecodes.EV_KEY in device.capabilities():
                    # Check if it has typical keyboard keys
                    keys = device.capabilities()[ecodes.EV_KEY]
                    if any(key in keys for key in [ecodes.KEY_A, ecodes.KEY_SPACE, ecodes.KEY_ENTER]):
                        devices.append(device)
                        print(f"Found keyboard device: {device.name} at {device.path}")
            except (OSError, PermissionError) as e:
                print(f"Cannot access device {path}: {e}")
        
        return devices
    
    def _check_permissions(self) -> bool:
        """Check if we have permission to access input devices."""
        devices = self._find_keyboard_devices()
        if not devices:
            print("No keyboard devices found. Check permissions.")
            print("You may need to:")
            print("1. Add your user to the 'input' group: sudo usermod -a -G input $USER")
            print("2. Create udev rules for input device access")
            print("3. Log out and log back in")
            return False
        return True
    
    async def start(self) -> bool:
        """Start monitoring for global hotkeys."""
        if self.running:
            return True
        
        if not self._check_permissions():
            return False
        
        self.devices = self._find_keyboard_devices()
        if not self.devices:
            return False
        
        self.running = True
        
        # Load shortcuts configuration
        self.shortcut_config.load_config()
        
        # Start monitoring in a separate thread
        self.monitor_thread = threading.Thread(target=self._monitor_devices, daemon=True)
        self.monitor_thread.start()
        
        print(f"Hotkey manager started with {len(self.devices)} keyboard devices")
        return True
    
    def stop(self):
        """Stop hotkey monitoring."""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        for device in self.devices:
            device.close()
        self.devices.clear()
        print("Hotkey manager stopped")
    
    def _monitor_devices(self):
        """Monitor keyboard devices for hotkey combinations."""
        try:
            # Create a selector for multiple devices
            devices_dict = {dev.fd: dev for dev in self.devices}
            
            while self.running:
                # Use select to wait for events from any device
                import select
                ready_fds, _, _ = select.select(devices_dict.keys(), [], [], 0.1)
                
                for fd in ready_fds:
                    device = devices_dict[fd]
                    try:
                        for event in device.read():
                            self._handle_event(event)
                    except OSError:
                        # Device was disconnected
                        print(f"Device {device.name} disconnected")
                        continue
                        
        except Exception as e:
            print(f"Error in hotkey monitoring: {e}")
        finally:
            print("Hotkey monitoring thread ended")
    
    def _handle_event(self, event):
        """Handle a keyboard event."""
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            
            if key_event.keystate == key_event.key_down:
                self.pressed_keys.add(event.code)
                self._check_shortcuts()
            elif key_event.keystate == key_event.key_up:
                self.pressed_keys.discard(event.code)
    
    def _check_shortcuts(self):
        """Check if current pressed keys match any configured shortcuts."""
        for action, shortcut in self.shortcut_config.get_enabled_shortcuts().items():
            if self._is_shortcut_pressed(shortcut):
                self._trigger_shortcut(action, shortcut)
    
    def _is_shortcut_pressed(self, shortcut: Shortcut) -> bool:
        """Check if a specific shortcut is currently pressed."""
        required_keys = set()
        
        # Add modifier keys
        for modifier in shortcut.modifiers:
            modifier_lower = modifier.lower()
            if modifier_lower in self.modifier_keys:
                required_keys.add(self.modifier_keys[modifier_lower])
                # Also check right variants
                if modifier_lower == 'ctrl':
                    if ecodes.KEY_RIGHTCTRL not in self.pressed_keys:
                        if ecodes.KEY_LEFTCTRL not in self.pressed_keys:
                            return False
                elif modifier_lower == 'alt':
                    if ecodes.KEY_RIGHTALT not in self.pressed_keys:
                        if ecodes.KEY_LEFTALT not in self.pressed_keys:
                            return False
                elif modifier_lower == 'shift':
                    if ecodes.KEY_RIGHTSHIFT not in self.pressed_keys:
                        if ecodes.KEY_LEFTSHIFT not in self.pressed_keys:
                            return False
        
        # Add main key
        key_lower = shortcut.key.lower()
        if key_lower in self.key_mapping:
            required_keys.add(self.key_mapping[key_lower])
        else:
            return False
        
        # Check if all required keys are pressed and no extra keys
        return required_keys.issubset(self.pressed_keys)
    
    def _trigger_shortcut(self, action: str, shortcut: Shortcut):
        """Trigger a shortcut action."""
        print(f"Shortcut triggered: {action} ({shortcut.get_key_combination()})")
        
        # Get callback from shortcut config
        callback = self.shortcut_config.get_callback(action)
        if callback:
            try:
                # Run callback in a thread to avoid blocking
                threading.Thread(target=callback, daemon=True).start()
            except Exception as e:
                print(f"Error executing shortcut callback: {e}")
        else:
            print(f"No callback registered for action: {action}")
    
    def register_shortcut_callback(self, action: str, callback: Callable):
        """Register a callback for a specific shortcut action."""
        self.shortcut_config.register_callback(action, callback)
    
    def add_shortcut(self, action: str, key: str, modifiers: List[str], 
                    callback: Optional[Callable] = None, description: str = ""):
        """Add a new shortcut."""
        if not self.shortcut_config.validate_shortcut(key, modifiers):
            raise ValueError(f"Invalid shortcut: {key} with modifiers {modifiers}")
        
        if self.shortcut_config.is_shortcut_conflict(key, modifiers):
            raise ValueError(f"Shortcut conflict: {key} with modifiers {modifiers}")
        
        self.shortcut_config.set_shortcut(action, key, modifiers, description)
        
        if callback:
            self.register_shortcut_callback(action, callback)
    
    def remove_shortcut(self, action: str):
        """Remove a shortcut."""
        self.shortcut_config.remove_shortcut(action)
    
    def get_shortcuts(self) -> Dict[str, Shortcut]:
        """Get all configured shortcuts."""
        return self.shortcut_config.get_all_shortcuts()