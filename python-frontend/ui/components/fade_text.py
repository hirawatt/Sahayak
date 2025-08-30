"""
Fade text component - Python equivalent of Swift FadeInTextView
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal


class FadeText(QWidget):
    """Animated fade-in text widget - equivalent to Swift FadeInTextView"""
    
    # Signals
    animation_finished = pyqtSignal()
    
    def __init__(self, text: str = "", fade_duration: int = 800):
        super().__init__()
        self.text = text
        self.fade_duration = fade_duration
        
        self._setup_ui()
        self._setup_animation()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_label = QLabel(self.text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: 500;
                line-height: 1.4;
            }
        """)
        
        # Setup opacity effect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.text_label.setGraphicsEffect(self.opacity_effect)
        
        layout.addWidget(self.text_label)
        self.setLayout(layout)
    
    def _setup_animation(self):
        """Setup fade animation"""
        try:
            self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_animation.setDuration(self.fade_duration)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
            self.fade_animation.finished.connect(self.animation_finished.emit)
        except Exception as e:
            # Fallback: just show the text without animation
            self.opacity_effect.setOpacity(1.0)
    
    def fade_in(self, text: str = None, delay: int = 0):
        """Start fade-in animation"""
        if text is not None:
            self.setText(text)
        
        if delay > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(delay, self._start_fade)
        else:
            self._start_fade()
    
    def fade_out(self):
        """Start fade-out animation"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
    
    def _start_fade(self):
        """Internal method to start fade animation"""
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def setText(self, text: str):
        """Update the text"""
        self.text = text
        self.text_label.setText(text)
    
    def setStyleSheet(self, style: str):
        """Override to apply style to label"""
        self.text_label.setStyleSheet(style)