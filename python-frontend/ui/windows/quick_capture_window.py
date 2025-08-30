"""
Quick Capture Window - Python equivalent of Swift QuickCaptureOverlay
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap

from ui.windows.base_window import BaseOverlayWindow
from ui.components.fade_text import FadeText
from config.settings import Settings


class QuickCaptureWindow(BaseOverlayWindow):
    """Quick Capture overlay window - equivalent to Swift QuickCaptureOverlay"""
    
    # Signals
    capture_saved = pyqtSignal(str)
    window_closed = pyqtSignal()
    
    def __init__(self, settings: Settings, backend_client=None):
        super().__init__(
            width=settings.windows.quick_capture_width,
            height=settings.windows.quick_capture_height,
            title="Quick Capture"
        )
        self.settings = settings
        self.backend_client = backend_client
        self.logger = logging.getLogger(__name__)
        
        # State
        self.captured_text = ""
        self.screenshot_data = None
        
        # UI Components
        self.capture_input: Optional[QTextEdit] = None
        self.save_button: Optional[QPushButton] = None
        self.status_label: Optional[FadeText] = None
        
        self._setup_ui()
        self._connect_backend()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header with close button
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Quick Capture")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        close_button = QPushButton("✕")
        close_button.setFixedSize(24, 24)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 12px;
                background-color: rgba(255, 255, 255, 0.1);
                color: #666;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button)
        
        main_layout.addLayout(header_layout)
        
        # Status label
        self.status_label = FadeText("Capture your thoughts instantly")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 14px;
                font-style: italic;
            }
        """)
        main_layout.addWidget(self.status_label)
        
        # Capture input area
        self.capture_input = QTextEdit()
        self.capture_input.setPlaceholderText("What's on your mind? Jot it down quickly...")
        self.capture_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 12px;
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                font-size: 14px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.capture_input.textChanged.connect(self._on_text_changed)
        
        main_layout.addWidget(self.capture_input)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        screenshot_button = QPushButton("📸 Screenshot")
        screenshot_button.clicked.connect(self._take_screenshot)
        screenshot_button.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 8px 16px;
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        button_layout.addWidget(screenshot_button)
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save Capture")
        self.save_button.clicked.connect(self._save_capture)
        self.save_button.setEnabled(False)
        self.save_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                background-color: #007AFF;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #0056CC;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.1);
                color: #666;
            }
        """)
        
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
        
        # Set main layout
        self.setLayout(main_layout)
        
        # Focus input on show
        self.capture_input.setFocus()
    
    def _connect_backend(self):
        """Connect to backend for context updates"""
        if self.backend_client:
            self.backend_client.register_message_handler('screenshot_taken', self._on_screenshot_taken)
            self.backend_client.register_message_handler('capture_saved', self._on_capture_saved)
    
    def _on_text_changed(self):
        """Handle text input changes"""
        text = self.capture_input.toPlainText().strip()
        self.save_button.setEnabled(bool(text))
    
    def _take_screenshot(self):
        """Take a screenshot"""
        if self.backend_client:
            asyncio.create_task(self._request_screenshot())
        else:
            self.status_label.fade_in("Screenshot feature requires backend connection")
    
    async def _request_screenshot(self):
        """Request screenshot from backend"""
        try:
            self.status_label.fade_in("Taking screenshot...")
            response = await self.backend_client.take_screenshot()
            
            if response.success:
                self.screenshot_data = response.data
                self.status_label.fade_in("Screenshot captured! 📸")
            else:
                self.status_label.fade_in(f"Screenshot failed: {response.error}")
                
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            self.status_label.fade_in("Screenshot error - check permissions")
    
    def _save_capture(self):
        """Save the capture"""
        text = self.capture_input.toPlainText().strip()
        if not text:
            return
        
        if self.backend_client:
            asyncio.create_task(self._save_to_backend(text))
        
        # Emit signal
        self.capture_saved.emit(text)
        
        # Clear and close
        self.capture_input.clear()
        self.close()
    
    async def _save_to_backend(self, text: str):
        """Save capture to backend"""
        try:
            capture_data = {
                'text': text,
                'screenshot': self.screenshot_data,
                'timestamp': asyncio.get_event_loop().time(),
                'type': 'quick_capture'
            }
            
            response = await self.backend_client.save_capture(capture_data)
            if not response.success:
                self.logger.error(f"Failed to save capture: {response.error}")
                
        except Exception as e:
            self.logger.error(f"Error saving capture: {e}")
    
    # Backend event handlers
    def _on_screenshot_taken(self, data: Dict[str, Any]):
        """Handle screenshot completion"""
        if data.get('success'):
            self.screenshot_data = data.get('data')
            self.status_label.fade_in("Screenshot attached! 📸")
        else:
            self.status_label.fade_in("Screenshot failed")
    
    def _on_capture_saved(self, data: Dict[str, Any]):
        """Handle capture save completion"""
        if data.get('success'):
            self.status_label.fade_in("Capture saved! ✅")
        else:
            self.status_label.fade_in("Save failed")
    
    def show(self):
        """Show window and focus input"""
        super().show()
        self.capture_input.setFocus()
        self.capture_input.clear()
        self.screenshot_data = None
        self.status_label.fade_in("Capture your thoughts instantly")
    
    def closeEvent(self, event):
        """Handle window close"""
        self.window_closed.emit()
        super().closeEvent(event)