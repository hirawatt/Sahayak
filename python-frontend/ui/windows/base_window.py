"""
Base overlay window class for all Horizon overlays
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class BaseOverlayWindow(QWidget):
    """Base class for all overlay windows"""
    
    # Signals
    window_closed = pyqtSignal()
    
    def __init__(self, width: int = 400, height: int = 300, title: str = "Horizon Overlay"):
        super().__init__()
        
        # Configure window
        self.setWindowTitle(title)
        self.setFixedSize(width, height)
        
        # Window flags for overlay behavior
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Position window (center of screen by default)
        self._center_on_screen()
        
        # Apply base styling
        self._apply_base_styling()
    
    def _center_on_screen(self):
        """Center the window on screen"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _apply_base_styling(self):
        """Apply base styling to the window"""
        self.setStyleSheet("""
            QWidget {
                border-radius: 12px;
                background-color: rgba(20, 20, 20, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.window_closed.emit()
        super().closeEvent(event)
    
    def show(self):
        """Show the window with focus"""
        super().show()
        self.raise_()
        self.activateWindow()