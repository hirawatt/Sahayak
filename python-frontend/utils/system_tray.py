"""
System tray management using PyGObject for GTK integration
"""

import logging
from typing import Optional, Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter
from pathlib import Path

from config.settings import Settings


class SystemTrayManager(QObject):
    """Manages system tray icon and menu"""
    
    # Signals
    quit_requested = pyqtSignal()
    
    def __init__(self, settings: Settings, overlay_manager=None, on_quit: Optional[Callable] = None):
        super().__init__()
        self.settings = settings
        self.overlay_manager = overlay_manager
        self.on_quit = on_quit
        self.logger = logging.getLogger(__name__)
        
        # System tray components
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.context_menu: Optional[QMenu] = None
        
        # Initialize if system tray is available
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._create_tray_icon()
            self._create_context_menu()
        else:
            self.logger.warning("System tray not available")
    
    def _create_tray_icon(self):
        """Create the system tray icon"""
        # Create default icon if no icon file exists
        icon = self._create_default_icon()
        
        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.setToolTip("Horizon Overlay")
        
        # Connect signals
        self.tray_icon.activated.connect(self._on_tray_activated)
    
    def _create_default_icon(self) -> QIcon:
        """Create a default icon"""
        # Try to load icon from assets
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "tray_icon.png"
        
        if icon_path.exists():
            return QIcon(str(icon_path))
        
        # Create a simple default icon
        pixmap = QPixmap(32, 32)
        pixmap.fill()
        
        painter = QPainter(pixmap)
        painter.setPen(self._get_theme_color())
        painter.drawEllipse(4, 4, 24, 24)
        painter.drawText(8, 20, "H")
        painter.end()
        
        return QIcon(pixmap)
    
    def _get_theme_color(self):
        """Get color based on current theme"""
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QApplication
        
        # Get system palette
        palette = QApplication.palette()
        return palette.color(palette.ColorRole.WindowText)
    
    def _create_context_menu(self):
        """Create the context menu"""
        if not self.tray_icon:
            return
        
        self.context_menu = QMenu()
        
        # AI Assist action
        ai_assist_action = QAction("AI Assist", self.context_menu)
        ai_assist_action.triggered.connect(self._toggle_ai_assist)
        self.context_menu.addAction(ai_assist_action)
        
        # Quick Capture action
        quick_capture_action = QAction("Quick Capture", self.context_menu)
        quick_capture_action.triggered.connect(self._toggle_quick_capture)
        self.context_menu.addAction(quick_capture_action)
        
        # Auto Context action
        auto_context_action = QAction("Auto Context", self.context_menu)
        auto_context_action.triggered.connect(self._toggle_auto_context)
        self.context_menu.addAction(auto_context_action)
        
        self.context_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self.context_menu)
        settings_action.triggered.connect(self._show_settings)
        self.context_menu.addAction(settings_action)
        
        self.context_menu.addSeparator()
        
        # About action
        about_action = QAction("About", self.context_menu)
        about_action.triggered.connect(self._show_about)
        self.context_menu.addAction(about_action)
        
        # Quit action
        quit_action = QAction("Quit", self.context_menu)
        quit_action.triggered.connect(self._quit_application)
        self.context_menu.addAction(quit_action)
        
        # Set context menu
        self.tray_icon.setContextMenu(self.context_menu)
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double-click shows AI Assist
            self._toggle_ai_assist()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle-click shows Quick Capture
            self._toggle_quick_capture()
    
    def _toggle_ai_assist(self):
        """Toggle AI Assist overlay"""
        if self.overlay_manager:
            import asyncio
            asyncio.create_task(self.overlay_manager.toggle_ai_assist())
    
    def _toggle_quick_capture(self):
        """Toggle Quick Capture overlay"""
        if self.overlay_manager:
            import asyncio
            asyncio.create_task(self.overlay_manager.toggle_quick_capture())
    
    def _toggle_auto_context(self):
        """Toggle Auto Context overlay"""
        if self.overlay_manager:
            import asyncio
            asyncio.create_task(self.overlay_manager.toggle_auto_context())
    
    def _show_settings(self):
        """Show settings window"""
        # This will be handled by the main app
        self.logger.info("Settings requested from tray")
    
    def _show_about(self):
        """Show about dialog"""
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox()
        msg.setWindowTitle("About Horizon Overlay")
        msg.setText("Horizon Overlay v1.0.0")
        msg.setInformativeText("AI-powered overlay for enhanced productivity")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
    
    def _quit_application(self):
        """Quit the application"""
        self.logger.info("Quit requested from tray")
        if self.on_quit:
            self.on_quit()
        self.quit_requested.emit()
    
    def show(self):
        """Show the system tray icon"""
        if self.tray_icon:
            self.tray_icon.show()
            self.logger.info("System tray icon shown")
    
    def hide(self):
        """Hide the system tray icon"""
        if self.tray_icon:
            self.tray_icon.hide()
            self.logger.info("System tray icon hidden")
    
    def show_message(self, title: str, message: str, icon=None):
        """Show notification message"""
        if self.tray_icon:
            if icon is None:
                icon = QSystemTrayIcon.MessageIcon.Information
            
            self.tray_icon.showMessage(title, message, icon, 3000)  # 3 second timeout
    
    def update_icon(self, icon_path: Optional[str] = None):
        """Update the tray icon"""
        if not self.tray_icon:
            return
        
        if icon_path and Path(icon_path).exists():
            icon = QIcon(icon_path)
        else:
            icon = self._create_default_icon()
        
        self.tray_icon.setIcon(icon)
    
    def update_tooltip(self, tooltip: str):
        """Update the tray icon tooltip"""
        if self.tray_icon:
            self.tray_icon.setToolTip(tooltip)
    
    def set_overlay_manager(self, overlay_manager):
        """Set the overlay manager reference"""
        self.overlay_manager = overlay_manager