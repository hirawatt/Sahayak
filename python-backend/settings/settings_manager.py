"""
Settings Manager for Horizon Overlay.
Central manager for all application settings and preferences.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from .user_preferences import UserPreferences
from .config_validator import ConfigValidator
from .theme_manager import ThemeManager

class SettingsManager:
    """Central settings management for Horizon Overlay."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or os.path.expanduser("~/.config/horizon-overlay")
        self.config_file = os.path.join(self.config_dir, "preferences.json")
        self.backup_file = os.path.join(self.config_dir, "preferences.backup.json")
        
        self._ensure_config_directory()
        
        self.preferences = UserPreferences()
        self.validator = ConfigValidator()
        self.theme_manager = ThemeManager()
        
        self.change_callbacks: Dict[str, list] = {}
        
        # Load existing preferences
        self.load_preferences()
    
    def _ensure_config_directory(self):
        """Ensure the configuration directory exists."""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
    
    def load_preferences(self) -> bool:
        """Load preferences from configuration file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Validate configuration
                if self.validator.validate_config(data):
                    self.preferences = UserPreferences.from_dict(data)
                    print("Preferences loaded successfully")
                    self._apply_theme()
                    return True
                else:
                    print("Invalid configuration file, using defaults")
                    return self._load_backup()
            else:
                print("No configuration file found, using defaults")
                self.save_preferences()  # Create default config
                return True
                
        except Exception as e:
            print(f"Error loading preferences: {e}")
            return self._load_backup()
    
    def _load_backup(self) -> bool:
        """Try to load backup configuration."""
        try:
            if os.path.exists(self.backup_file):
                with open(self.backup_file, 'r') as f:
                    data = json.load(f)
                
                if self.validator.validate_config(data):
                    self.preferences = UserPreferences.from_dict(data)
                    print("Backup preferences loaded successfully")
                    self._apply_theme()
                    return True
        except Exception as e:
            print(f"Error loading backup preferences: {e}")
        
        # If all else fails, use defaults
        self.preferences = UserPreferences()
        self.save_preferences()
        return True
    
    def save_preferences(self) -> bool:
        """Save preferences to configuration file."""
        try:
            # Create backup of current config
            if os.path.exists(self.config_file):
                import shutil
                shutil.copy2(self.config_file, self.backup_file)
            
            # Save new configuration
            data = self.preferences.to_dict()
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print("Preferences saved successfully")
            return True
            
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False
    
    def _apply_theme(self):
        """Apply the current theme settings."""
        self.theme_manager.set_theme(self.preferences.theme)
    
    def get_preferences(self) -> UserPreferences:
        """Get current user preferences."""
        return self.preferences
    
    def update_preferences(self, **kwargs) -> bool:
        """Update preferences with new values."""
        try:
            for key, value in kwargs.items():
                if hasattr(self.preferences, key):
                    setattr(self.preferences, key, value)
            
            success = self.save_preferences()
            if success:
                self._notify_change('preferences', kwargs)
            return success
            
        except Exception as e:
            print(f"Error updating preferences: {e}")
            return False
    
    def update_voice_settings(self, **kwargs) -> bool:
        """Update voice input settings."""
        try:
            self.preferences.update_voice_settings(**kwargs)
            success = self.save_preferences()
            if success:
                self._notify_change('voice', kwargs)
            return success
        except Exception as e:
            print(f"Error updating voice settings: {e}")
            return False
    
    def update_overlay_settings(self, **kwargs) -> bool:
        """Update overlay settings."""
        try:
            self.preferences.update_overlay_settings(**kwargs)
            success = self.save_preferences()
            if success:
                self._notify_change('overlay', kwargs)
            return success
        except Exception as e:
            print(f"Error updating overlay settings: {e}")
            return False
    
    def update_ai_settings(self, **kwargs) -> bool:
        """Update AI settings."""
        try:
            self.preferences.update_ai_settings(**kwargs)
            success = self.save_preferences()
            if success:
                self._notify_change('ai', kwargs)
            return success
        except Exception as e:
            print(f"Error updating AI settings: {e}")
            return False
    
    def set_theme(self, theme: str) -> bool:
        """Set application theme."""
        try:
            from .user_preferences import Theme
            theme_enum = Theme(theme)
            self.preferences.theme = theme_enum
            self.theme_manager.set_theme(theme_enum)
            
            success = self.save_preferences()
            if success:
                self._notify_change('theme', {'theme': theme})
            return success
            
        except ValueError:
            print(f"Invalid theme: {theme}")
            return False
        except Exception as e:
            print(f"Error setting theme: {e}")
            return False
    
    def add_shortcut(self, action: str, key: str, modifiers: list, enabled: bool = True) -> bool:
        """Add or update a keyboard shortcut."""
        try:
            self.preferences.set_shortcut(action, key, modifiers, enabled)
            success = self.save_preferences()
            if success:
                self._notify_change('shortcuts', {action: {'key': key, 'modifiers': modifiers, 'enabled': enabled}})
            return success
        except Exception as e:
            print(f"Error adding shortcut: {e}")
            return False
    
    def remove_shortcut(self, action: str) -> bool:
        """Remove a keyboard shortcut."""
        try:
            self.preferences.remove_shortcut(action)
            success = self.save_preferences()
            if success:
                self._notify_change('shortcuts', {action: None})
            return success
        except Exception as e:
            print(f"Error removing shortcut: {e}")
            return False
    
    def set_custom_setting(self, key: str, value: Any) -> bool:
        """Set a custom setting."""
        try:
            self.preferences.set_custom_setting(key, value)
            success = self.save_preferences()
            if success:
                self._notify_change('custom', {key: value})
            return success
        except Exception as e:
            print(f"Error setting custom setting: {e}")
            return False
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom setting."""
        return self.preferences.get_custom_setting(key, default)
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults."""
        try:
            self.preferences = UserPreferences()
            self._apply_theme()
            success = self.save_preferences()
            if success:
                self._notify_change('reset', {})
            return success
        except Exception as e:
            print(f"Error resetting to defaults: {e}")
            return False
    
    def export_settings(self, file_path: str) -> bool:
        """Export settings to a file."""
        try:
            data = self.preferences.to_dict()
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Settings exported to {file_path}")
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """Import settings from a file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if self.validator.validate_config(data):
                self.preferences = UserPreferences.from_dict(data)
                self._apply_theme()
                success = self.save_preferences()
                if success:
                    self._notify_change('import', data)
                    print(f"Settings imported from {file_path}")
                return success
            else:
                print("Invalid settings file")
                return False
                
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def register_change_callback(self, category: str, callback: Callable):
        """Register a callback for settings changes."""
        if category not in self.change_callbacks:
            self.change_callbacks[category] = []
        self.change_callbacks[category].append(callback)
    
    def unregister_change_callback(self, category: str, callback: Callable):
        """Unregister a callback for settings changes."""
        if category in self.change_callbacks:
            try:
                self.change_callbacks[category].remove(callback)
            except ValueError:
                pass
    
    def _notify_change(self, category: str, changes: Dict[str, Any]):
        """Notify registered callbacks about changes."""
        if category in self.change_callbacks:
            for callback in self.change_callbacks[category]:
                try:
                    callback(changes)
                except Exception as e:
                    print(f"Error in change callback: {e}")
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about the configuration."""
        return {
            'config_dir': self.config_dir,
            'config_file': self.config_file,
            'config_exists': os.path.exists(self.config_file),
            'backup_exists': os.path.exists(self.backup_file),
            'theme': self.preferences.theme.value,
            'first_run': self.preferences.first_run,
            'shortcuts_count': len(self.preferences.shortcuts),
            'custom_settings_count': len(self.preferences.custom)
        }