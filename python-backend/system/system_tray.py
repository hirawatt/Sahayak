"""
System Tray Manager for Horizon Overlay.
Provides GNOME Shell system tray integration for Ubuntu/Wayland.
"""

import asyncio
import subprocess
import json
import os
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import tempfile
import time

class SystemTrayManager:
    """System tray integration for GNOME Shell."""
    
    def __init__(self):
        self.is_active = False
        self.extension_uuid = "horizon-ai-assistant@cluely.com"
        self.extension_dir = Path.home() / ".local/share/gnome-shell/extensions" / self.extension_uuid
        self.temp_dir = Path(tempfile.gettempdir()) / "horizon-tray"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Callbacks
        self.on_menu_item_clicked: Optional[Callable[[str], None]] = None
        self.on_settings_clicked: Optional[Callable[[], None]] = None
        self.on_quit_clicked: Optional[Callable[[], None]] = None
        
        # Menu items
        self.menu_items = [
            {"id": "ai_assist", "label": "AI Assist", "action": "toggle_ai_assist"},
            {"id": "auto_context", "label": "Auto Context", "action": "toggle_auto_context"},
            {"id": "quick_capture", "label": "Quick Capture", "action": "toggle_quick_capture"},
            {"id": "separator", "label": "---", "action": None},
            {"id": "settings", "label": "Settings", "action": "show_settings"},
            {"id": "about", "label": "About", "action": "show_about"},
            {"id": "quit", "label": "Quit", "action": "quit_application"}
        ]
    
    async def setup(self) -> bool:
        """Setup system tray integration."""
        try:
            # Check if GNOME Shell is running
            if not await self._is_gnome_shell_running():
                print("GNOME Shell not detected, using fallback tray")
                return await self._setup_fallback_tray()
            
            # Create GNOME Shell extension
            if await self._create_gnome_extension():
                await self._install_extension()
                await self._enable_extension()
                self.is_active = True
                print("System tray integration activated")
                return True
            else:
                return await self._setup_fallback_tray()
                
        except Exception as e:
            print(f"Failed to setup system tray: {e}")
            return await self._setup_fallback_tray()
    
    async def _is_gnome_shell_running(self) -> bool:
        """Check if GNOME Shell is running."""
        try:
            result = await asyncio.create_subprocess_exec(
                'pgrep', '-x', 'gnome-shell',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False
    
    async def _create_gnome_extension(self) -> bool:
        """Create GNOME Shell extension for system tray."""
        try:
            # Create extension directory
            self.extension_dir.mkdir(parents=True, exist_ok=True)
            
            # Create metadata.json
            metadata = {
                "uuid": self.extension_uuid,
                "name": "Horizon AI Assistant",
                "description": "System tray integration for Horizon AI Assistant",
                "shell-version": ["3.36", "3.38", "40", "41", "42", "43", "44", "45"],
                "url": "https://github.com/cluely/horizon-ai-assistant"
            }
            
            with open(self.extension_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create extension.js
            extension_js = self._generate_extension_js()
            with open(self.extension_dir / "extension.js", 'w') as f:
                f.write(extension_js)
            
            # Create prefs.js (for preferences)
            prefs_js = self._generate_prefs_js()
            with open(self.extension_dir / "prefs.js", 'w') as f:
                f.write(prefs_js)
            
            # Copy icon if available
            await self._copy_icon()
            
            print(f"GNOME extension created at {self.extension_dir}")
            return True
            
        except Exception as e:
            print(f"Failed to create GNOME extension: {e}")
            return False
    
    def _generate_extension_js(self) -> str:
        """Generate GNOME Shell extension JavaScript code."""
        return '''
const { St, Clutter, GObject, Gio } = imports.gi;
const Main = imports.ui.main;
const PanelMenu = imports.ui.panelMenu;
const PopupMenu = imports.ui.popupMenu;

const ExtensionUtils = imports.misc.extensionUtils;
const Me = ExtensionUtils.getCurrentExtension();

const HorizonIndicator = GObject.registerClass(
class HorizonIndicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'Horizon AI Assistant');
        
        // Create icon
        this._icon = new St.Icon({
            icon_name: 'applications-science-symbolic',
            style_class: 'system-status-icon'
        });
        this.add_child(this._icon);
        
        // Create menu
        this._createMenu();
        
        // Setup communication with Python backend
        this._setupBackendCommunication();
    }
    
    _createMenu() {
        // AI Assist
        this._aiAssistItem = new PopupMenu.PopupMenuItem('AI Assist');
        this._aiAssistItem.connect('activate', () => {
            this._sendAction('toggle_ai_assist');
        });
        this.menu.addMenuItem(this._aiAssistItem);
        
        // Auto Context
        this._autoContextItem = new PopupMenu.PopupMenuItem('Auto Context');
        this._autoContextItem.connect('activate', () => {
            this._sendAction('toggle_auto_context');
        });
        this.menu.addMenuItem(this._autoContextItem);
        
        // Quick Capture
        this._quickCaptureItem = new PopupMenu.PopupMenuItem('Quick Capture');
        this._quickCaptureItem.connect('activate', () => {
            this._sendAction('toggle_quick_capture');
        });
        this.menu.addMenuItem(this._quickCaptureItem);
        
        // Separator
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        
        // Settings
        this._settingsItem = new PopupMenu.PopupMenuItem('Settings');
        this._settingsItem.connect('activate', () => {
            this._sendAction('show_settings');
        });
        this.menu.addMenuItem(this._settingsItem);
        
        // About
        this._aboutItem = new PopupMenu.PopupMenuItem('About');
        this._aboutItem.connect('activate', () => {
            this._sendAction('show_about');
        });
        this.menu.addMenuItem(this._aboutItem);
        
        // Separator
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        
        // Quit
        this._quitItem = new PopupMenu.PopupMenuItem('Quit');
        this._quitItem.connect('activate', () => {
            this._sendAction('quit_application');
        });
        this.menu.addMenuItem(this._quitItem);
    }
    
    _setupBackendCommunication() {
        // Setup communication with Python backend via HTTP
        this._httpSession = new Gio.HttpClient();
        this._backendUrl = 'http://127.0.0.1:8000';
    }
    
    _sendAction(action) {
        // Send action to Python backend
        try {
            let url = `${this._backendUrl}/api/v1/tray/action`;
            let request = new Gio.HttpRequest({
                method: 'POST',
                uri: url,
                headers: {'Content-Type': 'application/json'}
            });
            
            let data = JSON.stringify({action: action});
            request.set_content(data);
            
            this._httpSession.send_async(request, null, (session, result) => {
                try {
                    let response = session.send_finish(result);
                    log(`Horizon: Action ${action} sent to backend`);
                } catch (error) {
                    log(`Horizon: Failed to send action ${action}: ${error}`);
                }
            });
        } catch (error) {
            log(`Horizon: Communication error: ${error}`);
        }
    }
    
    updateStatus(status) {
        // Update menu items based on application status
        if (status.ai_assist) {
            this._aiAssistItem.label.text = 'AI Assist (Active)';
        } else {
            this._aiAssistItem.label.text = 'AI Assist';
        }
        
        if (status.auto_context) {
            this._autoContextItem.label.text = 'Auto Context (Active)';
        } else {
            this._autoContextItem.label.text = 'Auto Context';
        }
        
        if (status.quick_capture) {
            this._quickCaptureItem.label.text = 'Quick Capture (Active)';
        } else {
            this._quickCaptureItem.label.text = 'Quick Capture';
        }
    }
});

class Extension {
    constructor() {
        this._indicator = null;
    }
    
    enable() {
        log('Horizon AI Assistant extension enabled');
        this._indicator = new HorizonIndicator();
        Main.panel.addToStatusArea('horizon-ai-assistant', this._indicator);
    }
    
    disable() {
        log('Horizon AI Assistant extension disabled');
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}

function init() {
    return new Extension();
}
'''
    
    def _generate_prefs_js(self) -> str:
        """Generate preferences JavaScript code."""
        return '''
const { Gtk, GObject } = imports.gi;
const ExtensionUtils = imports.misc.extensionUtils;

function init() {
    // Initialization code
}

function buildPrefsWidget() {
    let widget = new Gtk.Box({
        orientation: Gtk.Orientation.VERTICAL,
        margin_top: 20,
        margin_bottom: 20,
        margin_start: 20,
        margin_end: 20,
        spacing: 20
    });
    
    let title = new Gtk.Label({
        label: '<b>Horizon AI Assistant Settings</b>',
        use_markup: true,
        halign: Gtk.Align.START
    });
    widget.append(title);
    
    let description = new Gtk.Label({
        label: 'Configure your Horizon AI Assistant settings through the main application.',
        halign: Gtk.Align.START,
        wrap: true
    });
    widget.append(description);
    
    return widget;
}
'''
    
    async def _copy_icon(self):
        """Copy application icon for the extension."""
        try:
            # Try to find an appropriate icon
            icon_paths = [
                "/usr/share/pixmaps/horizon-ai-assistant.png",
                "/usr/share/icons/hicolor/48x48/apps/horizon-ai-assistant.png",
                str(Path(__file__).parent.parent / "assets" / "icon.png")
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    import shutil
                    shutil.copy2(icon_path, self.extension_dir / "icon.png")
                    break
                    
        except Exception as e:
            print(f"Could not copy icon: {e}")
    
    async def _install_extension(self):
        """Install the GNOME Shell extension."""
        try:
            # Enable the extension using gnome-extensions command
            result = await asyncio.create_subprocess_exec(
                'gnome-extensions', 'install', str(self.extension_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                print("GNOME extension installed successfully")
            else:
                print("Failed to install GNOME extension via gnome-extensions")
                
        except Exception as e:
            print(f"Extension installation failed: {e}")
    
    async def _enable_extension(self):
        """Enable the GNOME Shell extension."""
        try:
            # Enable the extension
            result = await asyncio.create_subprocess_exec(
                'gnome-extensions', 'enable', self.extension_uuid,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                print("GNOME extension enabled successfully")
            else:
                print("Failed to enable GNOME extension")
                
        except Exception as e:
            print(f"Extension enabling failed: {e}")
    
    async def _setup_fallback_tray(self) -> bool:
        """Setup fallback system tray using other methods."""
        try:
            # Try to use AppIndicator (Unity/Ubuntu)
            return await self._setup_appindicator()
        except Exception as e:
            print(f"Fallback tray setup failed: {e}")
            return False
    
    async def _setup_appindicator(self) -> bool:
        """Setup AppIndicator for fallback tray support."""
        try:
            # Create a simple script that creates an AppIndicator
            script_content = self._generate_appindicator_script()
            script_path = self.temp_dir / "tray_indicator.py"
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Start the indicator script
            self.indicator_process = await asyncio.create_subprocess_exec(
                'python3', str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            print("AppIndicator fallback tray started")
            self.is_active = True
            return True
            
        except Exception as e:
            print(f"AppIndicator setup failed: {e}")
            return False
    
    def _generate_appindicator_script(self) -> str:
        """Generate AppIndicator Python script."""
        return '''#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3
import requests
import json
import threading
import time

class HorizonTrayIndicator:
    def __init__(self):
        self.backend_url = "http://127.0.0.1:8000"
        
        # Create indicator
        self.indicator = AppIndicator3.Indicator.new(
            "horizon-ai-assistant",
            "applications-science",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Create menu
        self.create_menu()
        
        # Start status update thread
        self.status_thread = threading.Thread(target=self.update_status_loop, daemon=True)
        self.status_thread.start()
    
    def create_menu(self):
        menu = Gtk.Menu()
        
        # AI Assist
        self.ai_assist_item = Gtk.MenuItem(label="AI Assist")
        self.ai_assist_item.connect("activate", lambda x: self.send_action("toggle_ai_assist"))
        menu.append(self.ai_assist_item)
        
        # Auto Context
        self.auto_context_item = Gtk.MenuItem(label="Auto Context")
        self.auto_context_item.connect("activate", lambda x: self.send_action("toggle_auto_context"))
        menu.append(self.auto_context_item)
        
        # Quick Capture
        self.quick_capture_item = Gtk.MenuItem(label="Quick Capture")
        self.quick_capture_item.connect("activate", lambda x: self.send_action("toggle_quick_capture"))
        menu.append(self.quick_capture_item)
        
        # Separator
        separator = Gtk.SeparatorMenuItem()
        menu.append(separator)
        
        # Settings
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.connect("activate", lambda x: self.send_action("show_settings"))
        menu.append(settings_item)
        
        # About
        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", lambda x: self.send_action("show_about"))
        menu.append(about_item)
        
        # Separator
        separator2 = Gtk.SeparatorMenuItem()
        menu.append(separator2)
        
        # Quit
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda x: self.send_action("quit_application"))
        menu.append(quit_item)
        
        menu.show_all()
        self.indicator.set_menu(menu)
    
    def send_action(self, action):
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/tray/action",
                json={"action": action},
                timeout=5
            )
            print(f"Action {action} sent to backend")
        except Exception as e:
            print(f"Failed to send action {action}: {e}")
    
    def update_status_loop(self):
        while True:
            try:
                response = requests.get(f"{self.backend_url}/api/v1/overlay/states", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    self.update_menu_status(status)
            except Exception as e:
                pass  # Silently ignore connection errors
            time.sleep(5)  # Update every 5 seconds
    
    def update_menu_status(self, status):
        # Update menu item labels based on status
        if status.get("ai_assist", False):
            self.ai_assist_item.set_label("AI Assist (Active)")
        else:
            self.ai_assist_item.set_label("AI Assist")
        
        if status.get("auto_context", False):
            self.auto_context_item.set_label("Auto Context (Active)")
        else:
            self.auto_context_item.set_label("Auto Context")
        
        if status.get("quick_capture", False):
            self.quick_capture_item.set_label("Quick Capture (Active)")
        else:
            self.quick_capture_item.set_label("Quick Capture")

if __name__ == "__main__":
    indicator = HorizonTrayIndicator()
    Gtk.main()
'''
    
    async def update_status(self, status: Dict[str, Any]):
        """Update tray status based on application state."""
        if not self.is_active:
            return
        
        # For GNOME extension, we could send D-Bus signals
        # For AppIndicator, status is updated via HTTP polling
        try:
            # Write status to temp file for communication
            status_file = self.temp_dir / "status.json"
            with open(status_file, 'w') as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Failed to update tray status: {e}")
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for tray events."""
        if event == "menu_item_clicked":
            self.on_menu_item_clicked = callback
        elif event == "settings_clicked":
            self.on_settings_clicked = callback
        elif event == "quit_clicked":
            self.on_quit_clicked = callback
    
    async def handle_tray_action(self, action: str):
        """Handle action from system tray."""
        if action == "show_settings" and self.on_settings_clicked:
            self.on_settings_clicked()
        elif action == "quit_application" and self.on_quit_clicked:
            self.on_quit_clicked()
        elif self.on_menu_item_clicked:
            self.on_menu_item_clicked(action)
    
    async def cleanup(self):
        """Clean up system tray resources."""
        if hasattr(self, 'indicator_process'):
            try:
                self.indicator_process.terminate()
                await self.indicator_process.wait()
            except Exception:
                pass
        
        # Disable GNOME extension
        try:
            await asyncio.create_subprocess_exec(
                'gnome-extensions', 'disable', self.extension_uuid,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception:
            pass
        
        self.is_active = False
        print("System tray cleaned up")