"""
Shortcut model - Python equivalent of Shortcut.swift
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Shortcut:
    """Keyboard shortcut model"""
    key: str
    modifiers: List[str]
    
    def __str__(self) -> str:
        """String representation of shortcut"""
        if self.modifiers:
            return f"{'+'.join(self.modifiers)}+{self.key}"
        return self.key
    
    def __eq__(self, other) -> bool:
        """Check equality with another shortcut"""
        if not isinstance(other, Shortcut):
            return False
        return (self.key.lower() == other.key.lower() and 
                set(self.modifiers) == set(other.modifiers))