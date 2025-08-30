"""
Auto Context Window - Python equivalent of Swift AutoContextOverlay
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                            QPushButton, QLabel, QFrame, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ui.windows.base_window import BaseOverlayWindow
from ui.components.context_card import ContextCard
from ui.components.tag_chip import TagChip
from ui.components.shimmer_text import ShimmerText
from config.settings import Settings


class AutoContextWindow(BaseOverlayWindow):
    """Auto Context overlay window - equivalent to Swift AutoContextOverlay"""
    
    # Signals
    context_selected = pyqtSignal(dict)
    search_requested = pyqtSignal(str)
    window_closed = pyqtSignal()
    
    def __init__(self, settings: Settings, backend_client=None):
        super().__init__(
            width=settings.windows.auto_context_width,
            height=settings.windows.auto_context_height,
            title="Auto Context"
        )
        self.settings = settings
        self.backend_client = backend_client
        self.logger = logging.getLogger(__name__)
        
        # State
        self.context_items: List[Dict[str, Any]] = []
        self.current_tags: List[str] = []
        self.is_loading = False
        self.current_query = ""
        
        # UI Components
        self.search_input: Optional[QLineEdit] = None
        self.context_area: Optional[QScrollArea] = None
        self.loading_indicator: Optional[ShimmerText] = None
        self.tag_container: Optional[QWidget] = None
        
        self._setup_ui()
        self._connect_backend()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header with search and close
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Related Context")
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
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search your notes and context...")
        self.search_input.returnPressed.connect(self._perform_search)
        self.search_input.setStyleSheet("""
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
        main_layout.addWidget(self.search_input)
        
        # Tag container (initially hidden)
        self.tag_container = QWidget()
        self.tag_layout = QHBoxLayout(self.tag_container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(8)
        self.tag_container.hide()
        main_layout.addWidget(self.tag_container)
        
        # Loading indicator
        self.loading_indicator = ShimmerText("Analyzing context...")
        self.loading_indicator.hide()
        main_layout.addWidget(self.loading_indicator)
        
        # Context area
        self.context_area = QScrollArea()
        self.context_area.setWidgetResizable(True)
        self.context_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.context_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.context_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Context content widget
        self.context_widget = QWidget()
        self.context_layout = QVBoxLayout(self.context_widget)
        self.context_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.context_layout.setSpacing(8)
        
        # Empty state
        self.empty_label = QLabel("Context will appear here automatically based on your current activity")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                font-style: italic;
                padding: 40px 20px;
            }
        """)
        self.context_layout.addWidget(self.empty_label)
        
        self.context_area.setWidget(self.context_widget)
        main_layout.addWidget(self.context_area)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.clicked.connect(self._refresh_context)
        refresh_button.setStyleSheet("""
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
        
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Set main layout
        self.setLayout(main_layout)
        
        # Apply context-specific styling
        self._apply_context_styling()
    
    def _apply_context_styling(self):
        """Apply styling specific to context window"""
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def _connect_backend(self):
        """Connect to backend for context updates"""
        if self.backend_client:
            self.backend_client.register_message_handler('context_update', self._on_context_update)
            self.backend_client.register_message_handler('context_loading', self._on_context_loading)
            self.backend_client.register_message_handler('tags_update', self._on_tags_update)
    
    def _perform_search(self):
        """Perform context search"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        self.current_query = query
        self.search_requested.emit(query)
        
        if self.backend_client:
            # Use a thread to run the async operation
            import threading
            thread = threading.Thread(target=self._run_search_in_thread, args=(query,))
            thread.daemon = True
            thread.start()
        
        self._set_loading(True)
    
    def _run_search_in_thread(self, query: str):
        """Run the search operation in a separate thread"""
        try:
            import asyncio
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async operation
            loop.run_until_complete(self._search_backend(query))
            loop.close()
            
        except Exception as e:
            self.logger.error(f"Error in search thread: {e}")
            # Use QTimer to update UI from main thread
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._set_loading(False))
    
    async def _search_backend(self, query: str):
        """Search backend for context"""
        try:
            response = await self.backend_client.search_context(query)
            if response.success:
                # Schedule UI update on main thread
                from PyQt6.QtCore import QTimer
                items = response.data.get('items', [])
                QTimer.singleShot(0, lambda: self._update_context_items(items))
            else:
                self.logger.error(f"Context search failed: {response.error}")
                # Schedule UI update on main thread
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._set_loading(False))
                
        except Exception as e:
            self.logger.error(f"Error searching context: {e}")
            # Schedule UI update on main thread
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._set_loading(False))
            self._set_loading(False)
    
    def _refresh_context(self):
        """Refresh context based on current activity"""
        if self.backend_client:
            # Use a thread to run the async operation
            import threading
            thread = threading.Thread(target=self._run_refresh_in_thread)
            thread.daemon = True
            thread.start()
        
        self._set_loading(True)
    
    def _run_refresh_in_thread(self):
        """Run the refresh operation in a separate thread"""
        try:
            import asyncio
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async operation
            loop.run_until_complete(self._refresh_backend())
            loop.close()
            
        except Exception as e:
            self.logger.error(f"Error in refresh thread: {e}")
            # Use QTimer to update UI from main thread
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._set_loading(False))
    
    async def _refresh_backend(self):
        """Request context refresh from backend"""
        try:
            response = await self.backend_client.refresh_context()
            if response.success:
                # Schedule UI update on main thread
                from PyQt6.QtCore import QTimer
                items = response.data.get('items', [])
                QTimer.singleShot(0, lambda: self._update_context_items(items))
            else:
                self.logger.error(f"Context refresh failed: {response.error}")
                # Schedule UI update on main thread
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._set_loading(False))
                
        except Exception as e:
            self.logger.error(f"Error refreshing context: {e}")
            # Schedule UI update on main thread
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._set_loading(False))
    
    def _set_loading(self, loading: bool):
        """Set loading state"""
        self.is_loading = loading
        if loading:
            self.loading_indicator.show()
            self.loading_indicator.start_animation()
        else:
            self.loading_indicator.hide()
            self.loading_indicator.stop_animation()
    
    def _update_context_items(self, items: List[Dict[str, Any]]):
        """Update context items display"""
        # Clear existing items (except empty label)
        for i in reversed(range(self.context_layout.count())):
            item = self.context_layout.itemAt(i)
            if item and item.widget() != self.empty_label:
                widget = item.widget()
                self.context_layout.removeWidget(widget)
                widget.deleteLater()
        
        self.context_items = items
        
        if items:
            self.empty_label.hide()
            
            # Add context cards
            for item in items:
                card = ContextCard(item)
                card.clicked.connect(lambda data=item: self._on_context_selected(data))
                self.context_layout.addWidget(card)
        else:
            self.empty_label.show()
            self.empty_label.setText("No related context found")
        
        self._set_loading(False)
    
    def _update_tags(self, tags: List[str]):
        """Update tag display"""
        # Clear existing tags
        for i in reversed(range(self.tag_layout.count())):
            item = self.tag_layout.itemAt(i)
            if item:
                widget = item.widget()
                self.tag_layout.removeWidget(widget)
                widget.deleteLater()
        
        self.current_tags = tags
        
        if tags:
            for tag in tags[:8]:  # Limit to 8 tags
                chip = TagChip(tag)
                chip.clicked.connect(lambda t=tag: self._on_tag_clicked(t))
                self.tag_layout.addWidget(chip)
            
            self.tag_container.show()
        else:
            self.tag_container.hide()
    
    def _on_context_selected(self, context_data: Dict[str, Any]):
        """Handle context item selection"""
        self.context_selected.emit(context_data)
        self.logger.debug(f"Context selected: {context_data.get('title', 'Unknown')}")
    
    def _on_tag_clicked(self, tag: str):
        """Handle tag click"""
        self.search_input.setText(f"#{tag}")
        self._perform_search()
    
    # Backend event handlers
    def _on_context_update(self, data: Dict[str, Any]):
        """Handle context updates from backend"""
        items = data.get('items', [])
        self._update_context_items(items)
    
    def _on_context_loading(self, data: Dict[str, Any]):
        """Handle loading state updates"""
        loading = data.get('loading', False)
        self._set_loading(loading)
    
    def _on_tags_update(self, data: Dict[str, Any]):
        """Handle tag updates"""
        tags = data.get('tags', [])
        self._update_tags(tags)
    
    def show(self):
        """Show window and optionally refresh context"""
        super().show()
        
        # Auto-refresh on show if we have no context
        if not self.context_items and self.backend_client:
            self._refresh_context()
    
    def closeEvent(self, event):
        """Handle window close"""
        self.window_closed.emit()
        super().closeEvent(event)