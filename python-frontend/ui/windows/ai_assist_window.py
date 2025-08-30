"""
AI Assist Window - Python equivalent of Swift AIAssistView
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QLineEdit, QPushButton, QScrollArea, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QIcon

from ui.windows.base_window import BaseOverlayWindow
from ui.components.chat_bubble import ChatBubble
from ui.components.shimmer_text import ShimmerText
from ui.components.fade_text import FadeText
from config.settings import Settings


class AIAssistWindow(BaseOverlayWindow):
    """AI Assist overlay window - equivalent to Swift AIAssistView"""
    
    # Signals
    message_sent = pyqtSignal(str)
    window_closed = pyqtSignal()
    
    def __init__(self, settings: Settings, backend_client=None):
        super().__init__(
            width=settings.windows.ai_assist_width,
            height=settings.windows.ai_assist_height,
            title="AI Assist"
        )
        self.settings = settings
        self.backend_client = backend_client
        self.logger = logging.getLogger(__name__)
        
        # State
        self.messages: List[Dict[str, Any]] = []
        self.is_thinking = False
        self.has_selected_text = False
        self.selected_text = ""
        self.streaming_response = ""
        
        # UI Components
        self.chat_area: Optional[QScrollArea] = None
        self.input_field: Optional[QLineEdit] = None
        self.send_button: Optional[QPushButton] = None
        self.thinking_indicator: Optional[ShimmerText] = None
        self.selected_text_display: Optional[QWidget] = None
        
        self._setup_ui()
        self._setup_animations()
        self._connect_backend()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header with close button and history
        header_layout = QHBoxLayout()
        
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
        
        header_layout.addWidget(close_button)
        header_layout.addStretch()
        
        history_button = QPushButton("📝")
        history_button.setFixedSize(24, 24)
        history_button.clicked.connect(self._show_history)
        history_button.setStyleSheet(close_button.styleSheet())
        
        expand_button = QPushButton("⤢")
        expand_button.setFixedSize(24, 24)
        expand_button.clicked.connect(self._toggle_expand)
        expand_button.setStyleSheet(close_button.styleSheet())
        
        header_layout.addWidget(history_button)
        header_layout.addWidget(expand_button)
        
        main_layout.addLayout(header_layout)
        
        # Selected text display (initially hidden)
        self.selected_text_display = self._create_selected_text_display()
        main_layout.addWidget(self.selected_text_display)
        
        # Chat area
        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chat_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Chat content widget
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(8)
        
        self.chat_area.setWidget(self.chat_widget)
        main_layout.addWidget(self.chat_area)
        
        # Thinking indicator
        self.thinking_indicator = ShimmerText("AI is thinking...")
        self.thinking_indicator.hide()
        main_layout.addWidget(self.thinking_indicator)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("How can I help?")
        self.input_field.returnPressed.connect(self._send_message)
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.send_button = QPushButton("→")
        self.send_button.setFixedSize(36, 36)
        self.send_button.clicked.connect(self._send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 18px;
                background-color: #007AFF;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
            QPushButton:pressed {
                background-color: #004499;
            }
        """)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        main_layout.addLayout(input_layout)
        
        # Set main layout
        self.setLayout(main_layout)
        
        # Apply styling
        self._apply_styling()
    
    def _create_selected_text_display(self) -> QWidget:
        """Create the selected text display widget"""
        widget = QWidget()
        widget.hide()  # Initially hidden
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Header
        header = QLabel("Selected Text:")
        header.setStyleSheet("color: #888; font-size: 12px; font-weight: bold;")
        layout.addWidget(header)
        
        # Text content
        self.selected_text_label = QLabel()
        self.selected_text_label.setWordWrap(True)
        self.selected_text_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.selected_text_label)
        
        return widget
    
    def _setup_animations(self):
        """Setup UI animations"""
        # Fade animation for selected text using QGraphicsOpacityEffect
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self.selected_text_opacity_effect = QGraphicsOpacityEffect()
        self.selected_text_display.setGraphicsEffect(self.selected_text_opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.selected_text_opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
    
    def _apply_styling(self):
        """Apply window styling"""
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 0.95);
                color: white;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def _connect_backend(self):
        """Connect to backend for real-time updates"""
        if self.backend_client:
            # Register for AI message updates
            self.backend_client.register_message_handler('ai_response', self._on_ai_response)
            self.backend_client.register_message_handler('ai_thinking', self._on_ai_thinking)
            self.backend_client.register_message_handler('context_update', self._on_context_update)
    
    def _send_message(self):
        """Send message to AI"""
        message = self.input_field.text().strip()
        if not message:
            return
        
        # Clear input
        self.input_field.clear()
        
        # Add user message to chat
        self._add_message(message, is_user=True)
        
        # Show thinking indicator
        self._set_thinking(True)
        
        # Send to backend
        if self.backend_client:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._schedule_backend_send(message))
        
        # Emit signal
        self.message_sent.emit(message)
    
    def _schedule_backend_send(self, message: str):
        """Schedule backend send in event loop"""
        # Use threading approach like in auto_context_window
        import threading
        thread = threading.Thread(target=self._run_send_in_thread, args=(message,))
        thread.daemon = True
        thread.start()
    
    def _run_send_in_thread(self, message: str):
        """Run the send operation in a separate thread"""
        try:
            import asyncio
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async operation
            loop.run_until_complete(self._send_to_backend(message))
            loop.close()
            
        except Exception as e:
            self.logger.error(f"Error in send thread: {e}")
            # Use QTimer to update UI from main thread
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._add_message(f"Send error: {str(e)}", is_user=False, is_error=True))
            QTimer.singleShot(0, lambda: self._set_thinking(False))
    
    async def _send_to_backend(self, message: str):
        """Send message to backend"""
        try:
            # Log the attempt
            self.logger.info(f"Sending message to backend: {message[:50]}...")
            
            # Send message to backend (smarter_analysis=False by default)
            response = await self.backend_client.send_chat_message(message, smarter_analysis=False)
            
            if response.success:
                self.logger.info("Message sent successfully to backend")
                # The response will come through WebSocket or we need to poll for it
                # For now, just stop thinking indicator - response will come via WebSocket
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._set_thinking(False))
            else:
                self.logger.error(f"Backend returned error: {response.error}")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._add_message(f"Error: {response.error}", is_user=False, is_error=True))
                QTimer.singleShot(0, lambda: self._set_thinking(False))
                
        except Exception as e:
            self.logger.error(f"Error sending message to backend: {e}")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._add_message(f"Connection error: {str(e)}", is_user=False, is_error=True))
            QTimer.singleShot(0, lambda: self._set_thinking(False))
    
    def _add_message(self, message: str, is_user: bool = False, is_error: bool = False):
        """Add message to chat"""
        bubble = ChatBubble(message, is_user=is_user, is_error=is_error)
        self.chat_layout.addWidget(bubble)
        
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)
        
        # Store message
        import time
        self.messages.append({
            'content': message,
            'is_user': is_user,
            'is_error': is_error,
            'timestamp': time.time()
        })
    
    def _scroll_to_bottom(self):
        """Scroll chat to bottom"""
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _set_thinking(self, thinking: bool):
        """Set thinking state"""
        self.is_thinking = thinking
        if thinking:
            self.thinking_indicator.show()
            self.thinking_indicator.start_animation()
        else:
            self.thinking_indicator.hide()
            self.thinking_indicator.stop_animation()
    
    def _show_history(self):
        """Show chat history"""
        # TODO: Implement chat history dialog
        self.logger.info("Show history requested")
    
    def _toggle_expand(self):
        """Toggle expanded view"""
        current_size = self.size()
        if current_size.height() < 600:
            self.resize(current_size.width(), 700)
        else:
            self.resize(current_size.width(), self.settings.windows.ai_assist_height)
    
    def update_selected_text(self, text: str):
        """Update selected text from context"""
        self.selected_text = text
        self.has_selected_text = bool(text.strip())
        
        if self.has_selected_text:
            self.selected_text_label.setText(text[:200] + "..." if len(text) > 200 else text)
            self.selected_text_display.show()
        else:
            self.selected_text_display.hide()
    
    # Backend event handlers
    def _on_ai_response(self, data: Dict[str, Any]):
        """Handle AI response from backend"""
        if 'content' in data:
            self._add_message(data['content'], is_user=False)
        self._set_thinking(False)
    
    def _on_ai_thinking(self, data: Dict[str, Any]):
        """Handle AI thinking status"""
        thinking = data.get('thinking', False)
        self._set_thinking(thinking)
    
    def _on_context_update(self, data: Dict[str, Any]):
        """Handle context updates"""
        if 'selected_text' in data:
            self.update_selected_text(data['selected_text'])
    
    def closeEvent(self, event):
        """Handle window close"""
        self.window_closed.emit()
        super().closeEvent(event)