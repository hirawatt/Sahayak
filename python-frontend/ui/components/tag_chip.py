"""
Tag Chip component for displaying clickable tags
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class TagChip(QWidget):
    """Clickable tag chip widget"""
    
    # Signals
    clicked = pyqtSignal(str)
    
    def __init__(self, tag: str):
        super().__init__()
        self.tag = tag
        
        self._setup_ui()
        self._setup_animations()
    
    def _setup_ui(self):
        """Setup the chip UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        
        # Tag label
        self.tag_label = QLabel(f"#{self.tag}")
        self.tag_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 122, 255, 0.15);
                border: 1px solid rgba(0, 122, 255, 0.3);
                border-radius: 12px;
                padding: 4px 8px;
                color: #66b3ff;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        
        layout.addWidget(self.tag_label)
        self.setLayout(layout)
        
        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _setup_animations(self):
        """Setup hover animations"""
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(100)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tag)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        self.tag_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 122, 255, 0.25);
                border: 1px solid rgba(0, 122, 255, 0.5);
                border-radius: 12px;
                padding: 4px 8px;
                color: #80c5ff;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self.tag_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 122, 255, 0.15);
                border: 1px solid rgba(0, 122, 255, 0.3);
                border-radius: 12px;
                padding: 4px 8px;
                color: #66b3ff;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        super().leaveEvent(event)