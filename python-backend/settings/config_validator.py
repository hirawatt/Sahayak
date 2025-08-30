"""
Configuration Validator for Horizon Overlay.
Validates configuration data structure and values.
"""

from typing import Dict, Any, List
import json

class ConfigValidator:
    """Validates configuration data for correctness and safety."""
    
    def __init__(self):
        self.valid_themes = {"light", "dark", "auto"}
        self.valid_positions = {"center", "top_left", "top_right", "bottom_left", "bottom_right", "custom"}
        self.valid_keys = {
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
            "space", "enter", "escape", "tab", "backspace", "delete",
            "up", "down", "left", "right", "home", "end", "page_up", "page_down",
            "insert", "print_screen", "pause", "scroll_lock", "num_lock", "caps_lock"
        }
        self.valid_modifiers = {"ctrl", "alt", "shift", "cmd", "super", "meta"}
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate entire configuration."""
        try:
            # Validate basic structure
            if not isinstance(config, dict):
                return False
            
            # Validate theme
            if "theme" in config:
                if not self._validate_theme(config["theme"]):
                    return False
            
            # Validate shortcuts
            if "shortcuts" in config:
                if not self._validate_shortcuts(config["shortcuts"]):
                    return False
            
            # Validate voice settings
            if "voice" in config:
                if not self._validate_voice_settings(config["voice"]):
                    return False
            
            # Validate overlay settings
            if "overlay" in config:
                if not self._validate_overlay_settings(config["overlay"]):
                    return False
            
            # Validate AI settings
            if "ai" in config:
                if not self._validate_ai_settings(config["ai"]):
                    return False
            
            # Validate notification settings
            if "notifications" in config:
                if not self._validate_notification_settings(config["notifications"]):
                    return False
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False
    
    def _validate_theme(self, theme: str) -> bool:
        """Validate theme setting."""
        return isinstance(theme, str) and theme in self.valid_themes
    
    def _validate_shortcuts(self, shortcuts: Dict[str, Any]) -> bool:
        """Validate shortcuts configuration."""
        if not isinstance(shortcuts, dict):
            return False
        
        for action, shortcut in shortcuts.items():
            if not isinstance(action, str):
                return False
            
            if not isinstance(shortcut, dict):
                return False
            
            # Required fields
            if "key" not in shortcut or "modifiers" not in shortcut:
                return False
            
            # Validate key
            key = shortcut["key"]
            if not isinstance(key, str) or key.lower() not in self.valid_keys:
                return False
            
            # Validate modifiers
            modifiers = shortcut["modifiers"]
            if not isinstance(modifiers, list):
                return False
            
            for modifier in modifiers:
                if not isinstance(modifier, str) or modifier.lower() not in self.valid_modifiers:
                    return False
            
            # Validate enabled flag
            if "enabled" in shortcut:
                if not isinstance(shortcut["enabled"], bool):
                    return False
        
        return True
    
    def _validate_voice_settings(self, voice: Dict[str, Any]) -> bool:
        """Validate voice settings."""
        if not isinstance(voice, dict):
            return False
        
        # Validate enabled
        if "enabled" in voice:
            if not isinstance(voice["enabled"], bool):
                return False
        
        # Validate threshold
        if "threshold" in voice:
            threshold = voice["threshold"]
            if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
                return False
        
        # Validate silence duration
        if "silence_duration" in voice:
            duration = voice["silence_duration"]
            if not isinstance(duration, (int, float)) or duration < 0:
                return False
        
        # Validate device_id
        if "device_id" in voice:
            device_id = voice["device_id"]
            if device_id is not None and not isinstance(device_id, int):
                return False
        
        # Validate auto_transcribe
        if "auto_transcribe" in voice:
            if not isinstance(voice["auto_transcribe"], bool):
                return False
        
        return True
    
    def _validate_overlay_settings(self, overlay: Dict[str, Any]) -> bool:
        """Validate overlay settings."""
        if not isinstance(overlay, dict):
            return False
        
        # Validate position
        if "position" in overlay:
            position = overlay["position"]
            if not isinstance(position, str) or position not in self.valid_positions:
                return False
        
        # Validate coordinates
        for coord in ["custom_x", "custom_y"]:
            if coord in overlay:
                if not isinstance(overlay[coord], int):
                    return False
        
        # Validate opacity
        if "opacity" in overlay:
            opacity = overlay["opacity"]
            if not isinstance(opacity, (int, float)) or opacity < 0 or opacity > 1:
                return False
        
        # Validate timeout
        if "auto_hide_timeout" in overlay:
            timeout = overlay["auto_hide_timeout"]
            if not isinstance(timeout, (int, float)) or timeout < 0:
                return False
        
        # Validate boolean flags
        for flag in ["show_animations", "blur_background"]:
            if flag in overlay:
                if not isinstance(overlay[flag], bool):
                    return False
        
        return True
    
    def _validate_ai_settings(self, ai: Dict[str, Any]) -> bool:
        """Validate AI settings."""
        if not isinstance(ai, dict):
            return False
        
        # Validate model
        if "model" in ai:
            if not isinstance(ai["model"], str):
                return False
        
        # Validate temperature
        if "temperature" in ai:
            temp = ai["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                return False
        
        # Validate max_tokens
        if "max_tokens" in ai:
            tokens = ai["max_tokens"]
            if not isinstance(tokens, int) or tokens < 1 or tokens > 32000:
                return False
        
        # Validate boolean flags
        for flag in ["auto_context", "conversation_memory"]:
            if flag in ai:
                if not isinstance(ai[flag], bool):
                    return False
        
        # Validate system_prompt
        if "system_prompt" in ai:
            if not isinstance(ai["system_prompt"], str):
                return False
        
        return True
    
    def _validate_notification_settings(self, notifications: Dict[str, Any]) -> bool:
        """Validate notification settings."""
        if not isinstance(notifications, dict):
            return False
        
        # Validate boolean flags
        for flag in ["enabled", "sound_enabled", "desktop_notifications", "overlay_notifications"]:
            if flag in notifications:
                if not isinstance(notifications[flag], bool):
                    return False
        
        return True
    
    def validate_shortcut(self, key: str, modifiers: List[str]) -> bool:
        """Validate a single shortcut."""
        if not isinstance(key, str) or key.lower() not in self.valid_keys:
            return False
        
        if not isinstance(modifiers, list):
            return False
        
        for modifier in modifiers:
            if not isinstance(modifier, str) or modifier.lower() not in self.valid_modifiers:
                return False
        
        return True
    
    def get_validation_errors(self, config: Dict[str, Any]) -> List[str]:
        """Get detailed validation errors."""
        errors = []
        
        try:
            if not isinstance(config, dict):
                errors.append("Configuration must be a dictionary")
                return errors
            
            # Check theme
            if "theme" in config and not self._validate_theme(config["theme"]):
                errors.append(f"Invalid theme: {config['theme']}. Must be one of {self.valid_themes}")
            
            # Check shortcuts
            if "shortcuts" in config:
                shortcuts = config["shortcuts"]
                if not isinstance(shortcuts, dict):
                    errors.append("Shortcuts must be a dictionary")
                else:
                    for action, shortcut in shortcuts.items():
                        if not isinstance(shortcut, dict):
                            errors.append(f"Shortcut '{action}' must be a dictionary")
                            continue
                        
                        if "key" not in shortcut:
                            errors.append(f"Shortcut '{action}' missing 'key' field")
                        elif shortcut["key"].lower() not in self.valid_keys:
                            errors.append(f"Invalid key '{shortcut['key']}' in shortcut '{action}'")
                        
                        if "modifiers" not in shortcut:
                            errors.append(f"Shortcut '{action}' missing 'modifiers' field")
                        elif not isinstance(shortcut["modifiers"], list):
                            errors.append(f"Modifiers for shortcut '{action}' must be a list")
                        else:
                            for modifier in shortcut["modifiers"]:
                                if modifier.lower() not in self.valid_modifiers:
                                    errors.append(f"Invalid modifier '{modifier}' in shortcut '{action}'")
            
            # Add more detailed error checking for other sections...
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return errors