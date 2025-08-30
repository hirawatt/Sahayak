"""
Global Shortcut Manager for handling system-wide keyboard shortcuts
"""

import logging
from typing import Dict, Callable, Optional
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import QApplication

from config.settings import Settings


class ShortcutManager(QObject):
    """Manages global keyboard shortcuts"""
    
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Store shortcuts and their callbacks
        self.shortcuts: Dict[str, QShortcut] = {}
        self.callbacks: Dict[str, Callable] = {}
    
    def register_shortcut(self, name: str, key_sequence: str, callback: Callable):
        """Register a global shortcut"""
        try:
            # Create QShortcut
            shortcut = QShortcut(QKeySequence(key_sequence), None)
            shortcut.activated.connect(callback)
            
            # Store references
            self.shortcuts[name] = shortcut
            self.callbacks[name] = callback
            
            self.logger.info(f"Registered shortcut '{name}': {key_sequence}")
            
        except Exception as e:
            self.logger.error(f"Failed to register shortcut '{name}': {e}")
    
    def unregister_shortcut(self, name: str):
        """Unregister a shortcut"""
        if name in self.shortcuts:
            shortcut = self.shortcuts[name]
            shortcut.setEnabled(False)
            del self.shortcuts[name]
            del self.callbacks[name]
            self.logger.info(f"Unregistered shortcut '{name}'")
    
    def set_shortcut_enabled(self, name: str, enabled: bool):
        """Enable or disable a shortcut"""
        if name in self.shortcuts:
            self.shortcuts[name].setEnabled(enabled)
    
    def get_registered_shortcuts(self) -> Dict[str, str]:
        """Get all registered shortcuts"""
        return {name: shortcut.key().toString() for name, shortcut in self.shortcuts.items()}
    
    def cleanup(self):
        """Clean up all shortcuts"""
        for name in list(self.shortcuts.keys()):
            self.unregister_shortcut(name)
        self.logger.info("Shortcut manager cleaned up")