"""
Main application class for Horizon Overlay
"""

import sys
import asyncio
import logging
from typing import Optional
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon, QAction
import qasync

from config.settings import Settings
from utils.hotkeys import HotkeyManager
from utils.system_tray import SystemTrayManager
from services.backend_client import BackendClient
from ui.overlays.overlay_manager import OverlayManager
from ui.windows.settings_window import SettingsWindow


class HorizonApp:
    """Main application class"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.qt_app: Optional[QApplication] = None
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.system_tray: Optional[SystemTrayManager] = None
        self.backend_client: Optional[BackendClient] = None
        self.overlay_manager: Optional[OverlayManager] = None
        self.settings_window: Optional[SettingsWindow] = None
        
        # Application state
        self.is_running = False
        
    async def run(self):
        """Main application loop"""
        self.logger.info("Starting Horizon Overlay application")
        
        try:
            # Initialize Qt application
            self._init_qt_app()
            
            # Initialize core services
            await self._init_services()
            
            # Initialize UI components
            self._init_ui()
            
            # Start the application
            self.is_running = True
            self.logger.info("Application started successfully")
            
            # Run the Qt event loop
            await self._run_qt_loop()
            
        except Exception as e:
            self.logger.error(f"Application startup failed: {e}")
            raise
        finally:
            await self._cleanup()
    
    def _init_qt_app(self):
        """Initialize Qt application"""
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)  # Keep running when windows close
        self.qt_app.setApplicationName("Horizon Overlay")
        self.qt_app.setApplicationVersion("1.0.0")
        
        # Check for system tray support
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray not available")
    
    async def _init_services(self):
        """Initialize core services"""
        # Backend client
        self.backend_client = BackendClient(self.settings.backend)
        await self.backend_client.connect()
        
        # Hotkey manager
        self.hotkey_manager = HotkeyManager(self.settings.hotkeys)
        await self.hotkey_manager.start()
        
        # Register hotkey callbacks
        self.hotkey_manager.register_callback('ai_assist', self._toggle_ai_assist)
        self.hotkey_manager.register_callback('quick_capture', self._toggle_quick_capture)
        self.hotkey_manager.register_callback('auto_context', self._toggle_auto_context)
        self.hotkey_manager.register_callback('toggle_settings', self._toggle_settings)
    
    def _init_ui(self):
        """Initialize UI components"""
        # Overlay manager
        self.overlay_manager = OverlayManager(
            settings=self.settings,
            backend_client=self.backend_client
        )
        
        # System tray
        self.system_tray = SystemTrayManager(
            settings=self.settings,
            overlay_manager=self.overlay_manager,
            on_quit=self.quit
        )
        self.system_tray.show()
        
        # Settings window (created but not shown)
        self.settings_window = SettingsWindow(
            settings=self.settings,
            hotkey_manager=self.hotkey_manager
        )
    
    async def _run_qt_loop(self):
        """Run the Qt event loop asynchronously"""
        loop = asyncio.get_event_loop()
        
        # Create a timer to process events
        timer = QTimer()
        timer.timeout.connect(lambda: None)  # Just to keep the loop alive
        timer.start(100)  # 100ms interval
        
        # Wait for application to quit
        while self.is_running:
            self.qt_app.processEvents()
            await asyncio.sleep(0.01)
    
    async def _cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up application resources")
        
        self.is_running = False
        
        if self.hotkey_manager:
            await self.hotkey_manager.stop()
        
        if self.backend_client:
            await self.backend_client.disconnect()
        
        if self.overlay_manager:
            self.overlay_manager.hide_all()
        
        if self.system_tray:
            self.system_tray.hide()
        
        if self.qt_app:
            self.qt_app.quit()
    
    def quit(self):
        """Quit the application"""
        self.logger.info("Application quit requested")
        self.is_running = False
    
    # Hotkey callbacks
    async def _toggle_ai_assist(self):
        """Toggle AI Assist overlay"""
        if self.overlay_manager:
            await self.overlay_manager.toggle_ai_assist()
    
    async def _toggle_quick_capture(self):
        """Toggle Quick Capture overlay"""
        if self.overlay_manager:
            await self.overlay_manager.toggle_quick_capture()
    
    async def _toggle_auto_context(self):
        """Toggle Auto Context overlay"""
        if self.overlay_manager:
            await self.overlay_manager.toggle_auto_context()
    
    def _toggle_settings(self):
        """Toggle Settings window"""
        if self.settings_window:
            if self.settings_window.isVisible():
                self.settings_window.hide()
            else:
                self.settings_window.show()
                self.settings_window.raise_()
                self.settings_window.activateWindow()