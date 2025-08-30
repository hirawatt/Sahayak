"""
Theme Manager for Horizon Overlay.
Manages application themes and visual settings.
"""

from enum import Enum
from typing import Dict, Any, Optional
import json
import os

class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

class ThemeManager:
    """Manages application themes and styling."""
    
    def __init__(self):
        self.current_theme = Theme.AUTO
        self.themes = self._load_default_themes()
        self.custom_themes = {}
        self.theme_callbacks = []
    
    def _load_default_themes(self) -> Dict[str, Dict[str, Any]]:
        """Load default theme configurations."""
        return {
            "light": {
                "background": "#FFFFFF",
                "surface": "#F5F5F5",
                "primary": "#007AFF",
                "secondary": "#5856D6",
                "text_primary": "#000000",
                "text_secondary": "#666666",
                "border": "#E0E0E0",
                "accent": "#FF9500",
                "success": "#34C759",
                "warning": "#FF9500",
                "error": "#FF3B30",
                "overlay_background": "rgba(255, 255, 255, 0.95)",
                "shadow": "rgba(0, 0, 0, 0.1)",
                "blur_amount": 10,
                "animation_duration": 0.3,
                "border_radius": 8
            },
            "dark": {
                "background": "#000000",
                "surface": "#1C1C1E",
                "primary": "#0A84FF",
                "secondary": "#5E5CE6",
                "text_primary": "#FFFFFF",
                "text_secondary": "#AEAEB2",
                "border": "#38383A",
                "accent": "#FF9F0A",
                "success": "#30D158",
                "warning": "#FF9F0A",
                "error": "#FF453A",
                "overlay_background": "rgba(28, 28, 30, 0.95)",
                "shadow": "rgba(0, 0, 0, 0.3)",
                "blur_amount": 15,
                "animation_duration": 0.3,
                "border_radius": 8
            }
        }
    
    def set_theme(self, theme: Theme):
        """Set the current theme."""
        self.current_theme = theme
        self._notify_theme_change()
    
    def get_current_theme(self) -> Theme:
        """Get the current theme."""
        return self.current_theme
    
    def get_theme_colors(self, theme: Optional[Theme] = None) -> Dict[str, Any]:
        """Get colors for a specific theme or current theme."""
        if theme is None:
            theme = self.current_theme
        
        # Handle auto theme (would need system detection in real implementation)
        if theme == Theme.AUTO:
            # For now, default to dark
            theme = Theme.DARK
        
        theme_name = theme.value
        if theme_name in self.themes:
            return self.themes[theme_name].copy()
        elif theme_name in self.custom_themes:
            return self.custom_themes[theme_name].copy()
        else:
            # Fallback to light theme
            return self.themes["light"].copy()
    
    def add_custom_theme(self, name: str, colors: Dict[str, Any]) -> bool:
        """Add a custom theme."""
        try:
            # Validate theme structure
            required_keys = {
                "background", "surface", "primary", "secondary",
                "text_primary", "text_secondary", "border", "accent"
            }
            
            if not all(key in colors for key in required_keys):
                print(f"Custom theme '{name}' missing required color keys")
                return False
            
            self.custom_themes[name] = colors.copy()
            return True
            
        except Exception as e:
            print(f"Error adding custom theme: {e}")
            return False
    
    def remove_custom_theme(self, name: str) -> bool:
        """Remove a custom theme."""
        if name in self.custom_themes:
            del self.custom_themes[name]
            return True
        return False
    
    def get_available_themes(self) -> list:
        """Get list of available themes."""
        themes = list(self.themes.keys()) + list(self.custom_themes.keys())
        return themes
    
    def export_theme(self, theme_name: str, file_path: str) -> bool:
        """Export a theme to a file."""
        try:
            colors = None
            if theme_name in self.themes:
                colors = self.themes[theme_name]
            elif theme_name in self.custom_themes:
                colors = self.custom_themes[theme_name]
            
            if colors is None:
                print(f"Theme '{theme_name}' not found")
                return False
            
            theme_data = {
                "name": theme_name,
                "colors": colors
            }
            
            with open(file_path, 'w') as f:
                json.dump(theme_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error exporting theme: {e}")
            return False
    
    def import_theme(self, file_path: str) -> bool:
        """Import a theme from a file."""
        try:
            with open(file_path, 'r') as f:
                theme_data = json.load(f)
            
            if "name" not in theme_data or "colors" not in theme_data:
                print("Invalid theme file format")
                return False
            
            name = theme_data["name"]
            colors = theme_data["colors"]
            
            return self.add_custom_theme(name, colors)
            
        except Exception as e:
            print(f"Error importing theme: {e}")
            return False
    
    def get_css_variables(self, theme: Optional[Theme] = None) -> str:
        """Generate CSS variables for web components."""
        colors = self.get_theme_colors(theme)
        
        css_vars = ":root {\n"
        for key, value in colors.items():
            css_var_name = f"--horizon-{key.replace('_', '-')}"
            css_vars += f"  {css_var_name}: {value};\n"
        css_vars += "}"
        
        return css_vars
    
    def get_style_dict(self, theme: Optional[Theme] = None) -> Dict[str, str]:
        """Get theme colors as a style dictionary for GUI frameworks."""
        colors = self.get_theme_colors(theme)
        
        # Convert to style dictionary format
        style_dict = {}
        for key, value in colors.items():
            # Convert snake_case to camelCase for some frameworks
            camel_key = self._to_camel_case(key)
            style_dict[camel_key] = value
        
        return style_dict
    
    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    def register_theme_callback(self, callback):
        """Register a callback for theme changes."""
        self.theme_callbacks.append(callback)
    
    def unregister_theme_callback(self, callback):
        """Unregister a theme change callback."""
        if callback in self.theme_callbacks:
            self.theme_callbacks.remove(callback)
    
    def _notify_theme_change(self):
        """Notify all registered callbacks about theme change."""
        colors = self.get_theme_colors()
        for callback in self.theme_callbacks:
            try:
                callback(self.current_theme, colors)
            except Exception as e:
                print(f"Error in theme callback: {e}")
    
    def apply_system_theme(self):
        """Apply system theme if in auto mode."""
        if self.current_theme == Theme.AUTO:
            # In a real implementation, this would detect system theme
            # For now, we'll use a simple time-based approach or default
            import datetime
            hour = datetime.datetime.now().hour
            
            # Use dark theme during evening/night hours
            if 18 <= hour or hour <= 6:
                effective_theme = Theme.DARK
            else:
                effective_theme = Theme.LIGHT
            
            # Don't change the current_theme, just return the effective theme
            return effective_theme
        
        return self.current_theme
    
    def get_contrast_color(self, background_color: str) -> str:
        """Get appropriate text color for given background."""
        # Simple implementation - in reality would calculate luminance
        dark_backgrounds = ["#000000", "#1C1C1E", "#2C2C2E"]
        
        if background_color in dark_backgrounds or background_color.startswith("rgba(0,") or background_color.startswith("rgba(28,"):
            return self.get_theme_colors()["text_primary"]
        else:
            return self.get_theme_colors()["text_primary"]
    
    def create_gradient(self, color1: str, color2: str, direction: str = "to right") -> str:
        """Create a CSS gradient string."""
        return f"linear-gradient({direction}, {color1}, {color2})"
    
    def get_theme_info(self) -> Dict[str, Any]:
        """Get information about current theme state."""
        return {
            "current_theme": self.current_theme.value,
            "available_themes": self.get_available_themes(),
            "custom_themes_count": len(self.custom_themes),
            "theme_callbacks_count": len(self.theme_callbacks),
            "current_colors": self.get_theme_colors()
        }