#!/usr/bin/env python3
"""
Constella Horizon - Python Frontend Main Application
"""

import sys
import asyncio
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon, QAction

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from services.backend_client import BackendClient
from services.overlay_manager import OverlayManager
from ui.setup.setup_wizard import SetupWizard


class ConstellaHorizonApp:
    """Main application class"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep running when windows close
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.settings = Settings()
        self.backend_client = None
        self.overlay_manager = None
        self.system_tray = None
        
        # Application state
        self.is_setup_complete = False
        
        self.logger.info("Constella Horizon starting up...")
    
    def _setup_logging(self):
        """Setup application logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('horizon.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def initialize(self):
        """Initialize the application asynchronously"""
        try:
            # Load settings
            self.settings.load()
            
            # Check if setup is needed
            if not self.settings.is_setup_complete():
                await self._run_setup()
            else:
                self.is_setup_complete = True
            
            if self.is_setup_complete:
                # Connect to backend
                await self._connect_backend()
                
                # Initialize overlay manager
                self._setup_overlay_manager()
                
                # Setup system tray
                self._setup_system_tray()
                
                self.logger.info("Application initialized successfully")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            return False
    
    async def _run_setup(self):
        """Run the setup wizard"""
        self.logger.info("Running setup wizard...")
        
        try:
            setup_wizard = SetupWizard(self.settings)
            
            # Show setup wizard
            if setup_wizard.exec():
                # Setup completed successfully
                self.settings.mark_setup_complete()
                self.settings.save()
                self.is_setup_complete = True
                self.logger.info("Setup completed successfully")
            else:
                # Setup cancelled
                self.logger.info("Setup cancelled by user")
                sys.exit(0)
                
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            sys.exit(1)
    
    async def _connect_backend(self):
        """Connect to the Python backend"""
        try:
            self.backend_client = BackendClient(self.settings.backend)
            
            # Connect to backend
            connected = await self.backend_client.connect()
            if not connected:
                self.logger.warning("Failed to connect to backend - running in offline mode")
            else:
                self.logger.info("Connected to backend successfully")
                
        except Exception as e:
            self.logger.warning(f"Backend connection failed: {e} - running in offline mode")
    
    def _setup_overlay_manager(self):
        """Setup the overlay manager"""
        try:
            self.overlay_manager = OverlayManager(self.settings, self.backend_client)
            
            # Connect signals
            self.overlay_manager.overlay_shown.connect(self._on_overlay_shown)
            self.overlay_manager.overlay_hidden.connect(self._on_overlay_hidden)
            
            self.logger.info("Overlay manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to setup overlay manager: {e}")
    
    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray not available")
            return
        
        try:
            # Create system tray icon
            self.system_tray = QSystemTrayIcon(self.app)
            
            # Set icon (you may need to adjust the path)
            icon_path = Path(__file__).parent.parent / "Assets.xcassets" / "AppIcon.appiconset" / "mac-icon-cropped-64.png"
            if icon_path.exists():
                self.system_tray.setIcon(QIcon(str(icon_path)))
            else:
                # Fallback to a simple text icon
                self.system_tray.setIcon(self.app.style().standardIcon(self.app.style().StandardPixmap.SP_ComputerIcon))
            
            self.system_tray.setToolTip("Constella Horizon")
            
            # Create context menu
            menu = QMenu()
            
            # AI Assist action
            ai_assist_action = QAction("AI Assist", self.app)
            ai_assist_action.triggered.connect(self._show_ai_assist)
            menu.addAction(ai_assist_action)
            
            # Quick Capture action
            quick_capture_action = QAction("Quick Capture", self.app)
            quick_capture_action.triggered.connect(self._show_quick_capture)
            menu.addAction(quick_capture_action)
            
            # Auto Context action
            auto_context_action = QAction("Auto Context", self.app)
            auto_context_action.triggered.connect(self._show_auto_context)
            menu.addAction(auto_context_action)
            
            menu.addSeparator()
            
            # Settings action
            settings_action = QAction("Settings", self.app)
            settings_action.triggered.connect(self._show_settings)
            menu.addAction(settings_action)
            
            menu.addSeparator()
            
            # Quit action
            quit_action = QAction("Quit", self.app)
            quit_action.triggered.connect(self._quit_application)
            menu.addAction(quit_action)
            
            self.system_tray.setContextMenu(menu)
            self.system_tray.show()
            
            self.logger.info("System tray setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup system tray: {e}")
    
    def _show_ai_assist(self):
        """Show AI Assist window"""
        if self.overlay_manager:
            self.overlay_manager.toggle_ai_assist()
    
    def _show_quick_capture(self):
        """Show Quick Capture window"""
        if self.overlay_manager:
            self.overlay_manager.toggle_quick_capture()
    
    def _show_auto_context(self):
        """Show Auto Context window"""
        if self.overlay_manager:
            self.overlay_manager.toggle_auto_context()
    
    def _show_settings(self):
        """Show settings window"""
        # TODO: Implement settings window
        self.logger.info("Settings window requested (not implemented yet)")
    
    def _quit_application(self):
        """Quit the application"""
        self.logger.info("Application quit requested")
        self.cleanup()
        self.app.quit()
    
    def _on_overlay_shown(self, overlay_type: str):
        """Handle overlay shown"""
        self.logger.debug(f"Overlay shown: {overlay_type}")
    
    def _on_overlay_hidden(self, overlay_type: str):
        """Handle overlay hidden"""
        self.logger.debug(f"Overlay hidden: {overlay_type}")
    
    def cleanup(self):
        """Cleanup application resources"""
        try:
            if self.overlay_manager:
                self.overlay_manager.cleanup()
            
            if self.backend_client:
                asyncio.create_task(self.backend_client.disconnect())
            
            if self.system_tray:
                self.system_tray.hide()
            
            self.logger.info("Application cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def run(self):
        """Run the application"""
        # Setup async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize application
        async def init_and_run():
            success = await self.initialize()
            if not success:
                self.logger.error("Failed to initialize application")
                sys.exit(1)
        
        # Run initialization
        loop.run_until_complete(init_and_run())
        
        # Start Qt event loop
        try:
            exit_code = self.app.exec()
            self.logger.info(f"Application exited with code {exit_code}")
            return exit_code
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            self.cleanup()
            return 0
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            self.cleanup()
            return 1


def main():
    """Main entry point"""
    app = ConstellaHorizonApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())