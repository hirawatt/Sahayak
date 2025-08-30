"""
User Preferences Model for Horizon Overlay.
Defines user preference data structures and validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

class OverlayPosition(Enum):
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CUSTOM = "custom"

@dataclass
class ShortcutPreference:
    """User shortcut preference."""
    key: str
    modifiers: List[str]
    enabled: bool = True

@dataclass
class VoicePreferences:
    """Voice input preferences."""
    enabled: bool = True
    threshold: float = 0.01
    silence_duration: float = 2.0
    device_id: Optional[int] = None
    auto_transcribe: bool = False

@dataclass
class OverlayPreferences:
    """Overlay display preferences."""
    position: OverlayPosition = OverlayPosition.CENTER
    custom_x: int = 0
    custom_y: int = 0
    opacity: float = 0.95
    auto_hide_timeout: float = 10.0
    show_animations: bool = True
    blur_background: bool = True

@dataclass
class AIPreferences:
    """AI assistant preferences."""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2048
    auto_context: bool = True
    conversation_memory: bool = True
    system_prompt: str = ""

@dataclass
class NotificationPreferences:
    """Notification preferences."""
    enabled: bool = True
    sound_enabled: bool = False
    desktop_notifications: bool = True
    overlay_notifications: bool = True

@dataclass
class UserPreferences:
    """Complete user preferences model."""
    
    # General preferences
    theme: Theme = Theme.AUTO
    language: str = "en"
    first_run: bool = True
    auto_start: bool = False
    
    # Shortcuts
    shortcuts: Dict[str, ShortcutPreference] = field(default_factory=dict)
    
    # Voice input
    voice: VoicePreferences = field(default_factory=VoicePreferences)
    
    # Overlay settings
    overlay: OverlayPreferences = field(default_factory=OverlayPreferences)
    
    # AI settings
    ai: AIPreferences = field(default_factory=AIPreferences)
    
    # Notifications
    notifications: NotificationPreferences = field(default_factory=NotificationPreferences)
    
    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary for serialization."""
        return {
            'theme': self.theme.value,
            'language': self.language,
            'first_run': self.first_run,
            'auto_start': self.auto_start,
            'shortcuts': {
                action: {
                    'key': pref.key,
                    'modifiers': pref.modifiers,
                    'enabled': pref.enabled
                } for action, pref in self.shortcuts.items()
            },
            'voice': {
                'enabled': self.voice.enabled,
                'threshold': self.voice.threshold,
                'silence_duration': self.voice.silence_duration,
                'device_id': self.voice.device_id,
                'auto_transcribe': self.voice.auto_transcribe
            },
            'overlay': {
                'position': self.overlay.position.value,
                'custom_x': self.overlay.custom_x,
                'custom_y': self.overlay.custom_y,
                'opacity': self.overlay.opacity,
                'auto_hide_timeout': self.overlay.auto_hide_timeout,
                'show_animations': self.overlay.show_animations,
                'blur_background': self.overlay.blur_background
            },
            'ai': {
                'model': self.ai.model,
                'temperature': self.ai.temperature,
                'max_tokens': self.ai.max_tokens,
                'auto_context': self.ai.auto_context,
                'conversation_memory': self.ai.conversation_memory,
                'system_prompt': self.ai.system_prompt
            },
            'notifications': {
                'enabled': self.notifications.enabled,
                'sound_enabled': self.notifications.sound_enabled,
                'desktop_notifications': self.notifications.desktop_notifications,
                'overlay_notifications': self.notifications.overlay_notifications
            },
            'custom': self.custom
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create preferences from dictionary."""
        prefs = cls()
        
        # Basic preferences
        prefs.theme = Theme(data.get('theme', Theme.AUTO.value))
        prefs.language = data.get('language', 'en')
        prefs.first_run = data.get('first_run', True)
        prefs.auto_start = data.get('auto_start', False)
        
        # Shortcuts
        shortcuts_data = data.get('shortcuts', {})
        for action, shortcut_data in shortcuts_data.items():
            prefs.shortcuts[action] = ShortcutPreference(
                key=shortcut_data['key'],
                modifiers=shortcut_data['modifiers'],
                enabled=shortcut_data.get('enabled', True)
            )
        
        # Voice preferences
        voice_data = data.get('voice', {})
        prefs.voice = VoicePreferences(
            enabled=voice_data.get('enabled', True),
            threshold=voice_data.get('threshold', 0.01),
            silence_duration=voice_data.get('silence_duration', 2.0),
            device_id=voice_data.get('device_id'),
            auto_transcribe=voice_data.get('auto_transcribe', False)
        )
        
        # Overlay preferences
        overlay_data = data.get('overlay', {})
        prefs.overlay = OverlayPreferences(
            position=OverlayPosition(overlay_data.get('position', OverlayPosition.CENTER.value)),
            custom_x=overlay_data.get('custom_x', 0),
            custom_y=overlay_data.get('custom_y', 0),
            opacity=overlay_data.get('opacity', 0.95),
            auto_hide_timeout=overlay_data.get('auto_hide_timeout', 10.0),
            show_animations=overlay_data.get('show_animations', True),
            blur_background=overlay_data.get('blur_background', True)
        )
        
        # AI preferences
        ai_data = data.get('ai', {})
        prefs.ai = AIPreferences(
            model=ai_data.get('model', 'gpt-4'),
            temperature=ai_data.get('temperature', 0.7),
            max_tokens=ai_data.get('max_tokens', 2048),
            auto_context=ai_data.get('auto_context', True),
            conversation_memory=ai_data.get('conversation_memory', True),
            system_prompt=ai_data.get('system_prompt', '')
        )
        
        # Notification preferences
        notif_data = data.get('notifications', {})
        prefs.notifications = NotificationPreferences(
            enabled=notif_data.get('enabled', True),
            sound_enabled=notif_data.get('sound_enabled', False),
            desktop_notifications=notif_data.get('desktop_notifications', True),
            overlay_notifications=notif_data.get('overlay_notifications', True)
        )
        
        # Custom preferences
        prefs.custom = data.get('custom', {})
        
        return prefs
    
    def get_shortcut(self, action: str) -> Optional[ShortcutPreference]:
        """Get shortcut preference for an action."""
        return self.shortcuts.get(action)
    
    def set_shortcut(self, action: str, key: str, modifiers: List[str], enabled: bool = True):
        """Set shortcut preference for an action."""
        self.shortcuts[action] = ShortcutPreference(
            key=key,
            modifiers=modifiers,
            enabled=enabled
        )
    
    def remove_shortcut(self, action: str):
        """Remove shortcut preference for an action."""
        if action in self.shortcuts:
            del self.shortcuts[action]
    
    def update_voice_settings(self, **kwargs):
        """Update voice preferences."""
        for key, value in kwargs.items():
            if hasattr(self.voice, key):
                setattr(self.voice, key, value)
    
    def update_overlay_settings(self, **kwargs):
        """Update overlay preferences."""
        for key, value in kwargs.items():
            if hasattr(self.overlay, key):
                if key == 'position' and isinstance(value, str):
                    setattr(self.overlay, key, OverlayPosition(value))
                else:
                    setattr(self.overlay, key, value)
    
    def update_ai_settings(self, **kwargs):
        """Update AI preferences."""
        for key, value in kwargs.items():
            if hasattr(self.ai, key):
                setattr(self.ai, key, value)
    
    def set_custom_setting(self, key: str, value: Any):
        """Set a custom setting."""
        self.custom[key] = value
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom setting."""
        return self.custom.get(key, default)