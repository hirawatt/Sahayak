"""
Shortcut Configuration Manager for Horizon Overlay.
Handles shortcut definitions and customization.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
import json
from pathlib import Path
import os

@dataclass
class Shortcut:
    """Represents a keyboard shortcut configuration."""
    key: str
    modifiers: List[str]
    action: str
    description: str
    enabled: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'key': self.key,
            'modifiers': self.modifiers,
            'action': self.action,
            'description': self.description,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Shortcut':
        return cls(
            key=data['key'],
            modifiers=data['modifiers'],
            action=data['action'],
            description=data['description'],
            enabled=data.get('enabled', True)
        )
    
    def get_key_combination(self) -> str:
        """Get human-readable key combination."""
        parts = self.modifiers + [self.key]
        return '+'.join(parts)

class ShortcutConfig:
    """Manages shortcut configuration and persistence."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.expanduser("~/.config/horizon-overlay/shortcuts.json")
        self._ensure_config_directory()
        self.shortcuts: Dict[str, Shortcut] = {}
        self.action_callbacks: Dict[str, Callable] = {}
        self._load_default_shortcuts()
    
    def _ensure_config_directory(self):
        """Ensure the config directory exists."""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _load_default_shortcuts(self):
        """Load default shortcut configuration."""
        default_shortcuts = [
            Shortcut(
                key="1",
                modifiers=["ctrl", "shift"],
                action="ai_assist",
                description="Open AI Assist overlay"
            ),
            Shortcut(
                key="2", 
                modifiers=["ctrl", "shift"],
                action="quick_capture",
                description="Open Quick Capture overlay"
            ),
            Shortcut(
                key="o",
                modifiers=["ctrl", "shift"], 
                action="auto_context",
                description="Toggle Auto Context overlay"
            ),
            Shortcut(
                key="space",
                modifiers=["ctrl", "alt"],
                action="voice_activate",
                description="Voice activation toggle"
            ),
            Shortcut(
                key="escape",
                modifiers=[],
                action="close_overlay",
                description="Close current overlay"
            )
        ]
        
        for shortcut in default_shortcuts:
            self.shortcuts[shortcut.action] = shortcut
    
    def load_config(self):
        """Load shortcuts from configuration file."""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    
                for action, shortcut_data in data.items():
                    self.shortcuts[action] = Shortcut.from_dict(shortcut_data)
        except Exception as e:
            print(f"Error loading shortcut config: {e}")
            # Fall back to defaults
    
    def save_config(self):
        """Save current shortcuts to configuration file."""
        try:
            data = {}
            for action, shortcut in self.shortcuts.items():
                data[action] = shortcut.to_dict()
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving shortcut config: {e}")
    
    def get_shortcut(self, action: str) -> Optional[Shortcut]:
        """Get shortcut by action name."""
        return self.shortcuts.get(action)
    
    def set_shortcut(self, action: str, key: str, modifiers: List[str], description: str = ""):
        """Set or update a shortcut."""
        if action in self.shortcuts:
            self.shortcuts[action].key = key
            self.shortcuts[action].modifiers = modifiers
            if description:
                self.shortcuts[action].description = description
        else:
            self.shortcuts[action] = Shortcut(
                key=key,
                modifiers=modifiers,
                action=action,
                description=description
            )
        self.save_config()
    
    def remove_shortcut(self, action: str):
        """Remove a shortcut."""
        if action in self.shortcuts:
            del self.shortcuts[action]
            self.save_config()
    
    def enable_shortcut(self, action: str, enabled: bool = True):
        """Enable or disable a shortcut."""
        if action in self.shortcuts:
            self.shortcuts[action].enabled = enabled
            self.save_config()
    
    def get_all_shortcuts(self) -> Dict[str, Shortcut]:
        """Get all configured shortcuts."""
        return self.shortcuts.copy()
    
    def get_enabled_shortcuts(self) -> Dict[str, Shortcut]:
        """Get only enabled shortcuts."""
        return {action: shortcut for action, shortcut in self.shortcuts.items() 
                if shortcut.enabled}
    
    def register_callback(self, action: str, callback: Callable):
        """Register a callback function for an action."""
        self.action_callbacks[action] = callback
    
    def get_callback(self, action: str) -> Optional[Callable]:
        """Get callback function for an action."""
        return self.action_callbacks.get(action)
    
    def validate_shortcut(self, key: str, modifiers: List[str]) -> bool:
        """Validate if a shortcut combination is valid."""
        # Check if key is valid
        valid_keys = [
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            'space', 'enter', 'escape', 'tab', 'backspace', 'delete',
            'up', 'down', 'left', 'right',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12'
        ]
        
        if key.lower() not in valid_keys:
            return False
        
        # Check if modifiers are valid
        valid_modifiers = ['ctrl', 'alt', 'shift', 'super']
        for modifier in modifiers:
            if modifier.lower() not in valid_modifiers:
                return False
        
        return True
    
    def is_shortcut_conflict(self, key: str, modifiers: List[str], exclude_action: Optional[str] = None) -> bool:
        """Check if a shortcut combination conflicts with existing shortcuts."""
        for action, shortcut in self.shortcuts.items():
            if exclude_action and action == exclude_action:
                continue
            
            if (shortcut.key.lower() == key.lower() and 
                [m.lower() for m in shortcut.modifiers] == [m.lower() for m in modifiers]):
                return True
        
        return False