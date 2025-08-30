"""
Context Card component - Python equivalent of Swift ContextCard
"""

from typing import Dict, Any
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap


class ContextCard(QWidget):
    """Context card widget for displaying contextual information"""
    
    # Signals
    clicked = pyqtSignal(dict)
    
    def __init__(self, context_data: Dict[str, Any]):
        super().__init__()
        self.context_data = context_data
        
        self._setup_ui()
        self._setup_animations()
    
    def _setup_ui(self):
        """Setup the card UI"""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Header with title and type
        header_layout = QHBoxLayout()
        
        # Title
        title = self.context_data.get('title', 'Untitled')
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        
        # Type indicator
        context_type = self.context_data.get('type', 'note')
        type_icon = self._get_type_icon(context_type)
        self.type_label = QLabel(type_icon)
        self.type_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 12px;
                min-width: 20px;
            }
        """)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.type_label)
        
        layout.addLayout(header_layout)
        
        # Content preview
        content = self.context_data.get('content', '')
        if content:
            preview = content[:120] + "..." if len(content) > 120 else content
            self.content_label = QLabel(preview)
            self.content_label.setWordWrap(True)
            self.content_label.setStyleSheet("""
                QLabel {
                    color: #ccc;
                    font-size: 12px;
                    line-height: 1.3;
                }
            """)
            layout.addWidget(self.content_label)
        
        # Tags
        tags = self.context_data.get('tags', [])
        if tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)
            
            for tag in tags[:3]:  # Limit to 3 tags
                tag_label = QLabel(f"#{tag}")
                tag_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(0, 122, 255, 0.2);
                        border: 1px solid rgba(0, 122, 255, 0.3);
                        border-radius: 8px;
                        padding: 2px 6px;
                        color: #66b3ff;
                        font-size: 10px;
                        font-weight: 500;
                    }
                """)
                tags_layout.addWidget(tag_label)
            
            tags_layout.addStretch()
            layout.addLayout(tags_layout)
        
        # Metadata
        metadata_layout = QHBoxLayout()
        
        # Timestamp
        timestamp = self.context_data.get('timestamp')
        if timestamp:
            time_str = self._format_timestamp(timestamp)
            time_label = QLabel(time_str)
            time_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 10px;
                }
            """)
            metadata_layout.addWidget(time_label)
        
        # Score/relevance
        score = self.context_data.get('score')
        if score:
            score_label = QLabel(f"{score:.0%}")
            score_label.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            metadata_layout.addStretch()
            metadata_layout.addWidget(score_label)
        
        if metadata_layout.count() > 0:
            layout.addLayout(metadata_layout)
        
        self.setLayout(layout)
        
        # Apply card styling
        self._apply_card_styling()
        
        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _get_type_icon(self, context_type: str) -> str:
        """Get icon for context type"""
        icons = {
            'note': '📝',
            'document': '📄',
            'webpage': '🌐',
            'screenshot': '📸',
            'email': '📧',
            'chat': '💬',
            'code': '💻',
            'file': '📁'
        }
        return icons.get(context_type, '📄')
    
    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp for display"""
        import datetime
        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.datetime.fromisoformat(str(timestamp))
            
            now = datetime.datetime.now()
            diff = now - dt
            
            if diff.days > 7:
                return dt.strftime("%b %d")
            elif diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "Just now"
        except:
            return "Recent"
    
    def _apply_card_styling(self):
        """Apply card styling"""
        self.setStyleSheet("""
            ContextCard {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
            ContextCard:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
    
    def _setup_animations(self):
        """Setup hover animations"""
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.context_data)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        self.setStyleSheet("""
            ContextCard {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
        """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self.setStyleSheet("""
            ContextCard {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
        """)
        super().leaveEvent(event)