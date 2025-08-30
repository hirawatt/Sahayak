"""
Shimmer text component - Python equivalent of Swift ShimmerTextView
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QLinearGradient, QBrush, QColor


class ShimmerText(QWidget):
    """Animated shimmer text widget - equivalent to Swift ShimmerTextView"""
    
    def __init__(self, text: str = "Loading..."):
        super().__init__()
        self.text = text
        self.shimmer_position = 0.0
        self.is_animating = False
        
        self._setup_ui()
        self._setup_animation()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_label = QLabel(self.text)
        self.text_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 14px;
                font-style: italic;
            }
        """)
        
        layout.addWidget(self.text_label)
        self.setLayout(layout)
    
    def _setup_animation(self):
        """Setup shimmer animation"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_shimmer)
        self.animation_timer.setInterval(50)  # 20 FPS
    
    def start_animation(self):
        """Start the shimmer animation"""
        if not self.is_animating:
            self.is_animating = True
            self.animation_timer.start()
    
    def stop_animation(self):
        """Stop the shimmer animation"""
        if self.is_animating:
            self.is_animating = False
            self.animation_timer.stop()
            self._reset_appearance()
    
    def _update_shimmer(self):
        """Update shimmer effect"""
        self.shimmer_position += 0.05
        if self.shimmer_position > 1.0:
            self.shimmer_position = -0.3
        
        # Create shimmer effect by adjusting opacity
        opacity = 0.3 + 0.4 * abs(self.shimmer_position)
        self.text_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, {opacity});
                font-size: 14px;
                font-style: italic;
            }}
        """)
    
    def _reset_appearance(self):
        """Reset to normal appearance"""
        self.text_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 14px;
                font-style: italic;
            }
        """)
    
    def setText(self, text: str):
        """Update the text"""
        self.text = text
        self.text_label.setText(text)