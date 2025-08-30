"""
Chat bubble component for AI conversations
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPalette


class ChatBubble(QWidget):
    """Chat bubble widget for displaying messages"""
    
    def __init__(self, message: str, is_user: bool = False, is_error: bool = False):
        super().__init__()
        self.message = message
        self.is_user = is_user
        self.is_error = is_error
        
        self._setup_ui()
        self._animate_in()
    
    def _setup_ui(self):
        """Setup the bubble UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)
        
        # Create message label
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Style based on message type
        if self.is_error:
            bubble_color = "rgba(220, 53, 69, 0.2)"
            text_color = "#ff6b7a"
            border_color = "rgba(220, 53, 69, 0.3)"
        elif self.is_user:
            bubble_color = "rgba(0, 122, 255, 0.2)"
            text_color = "#ffffff"
            border_color = "rgba(0, 122, 255, 0.3)"
        else:
            bubble_color = "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"
            border_color = "rgba(255, 255, 255, 0.15)"
        
        self.message_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bubble_color};
                border: 1px solid {border_color};
                border-radius: 12px;
                padding: 8px 12px;
                color: {text_color};
                font-size: 14px;
                line-height: 1.4;
                max-width: 280px;
            }}
        """)
        
        # Align based on sender
        if self.is_user:
            layout.addStretch()
            layout.addWidget(self.message_label)
        else:
            layout.addWidget(self.message_label)
            layout.addStretch()
        
        self.setLayout(layout)
    
    def _animate_in(self):
        """Animate bubble appearance"""
        # Use QGraphicsOpacityEffect for proper opacity animation
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.fade_animation.start()