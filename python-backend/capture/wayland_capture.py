"""
Wayland Screenshot Capture for Horizon Overlay.
Handles screen capture on Ubuntu/Wayland using GNOME Shell D-Bus API.
"""

import asyncio
import subprocess
import tempfile
import os
from typing import Optional, Tuple
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from pathlib import Path
import time

class WaylandScreenCapture:
    """Screen capture manager for Wayland using GNOME Shell D-Bus API."""
    
    def __init__(self):
        self.bus = None
        self.screenshot_interface = None
        self.temp_dir = Path(tempfile.gettempdir()) / "horizon-screenshots"
        self.temp_dir.mkdir(exist_ok=True)
        self._init_dbus()
    
    def _init_dbus(self):
        """Initialize D-Bus connection to GNOME Shell."""
        try:
            # Initialize D-Bus main loop
            DBusGMainLoop(set_as_default=True)
            
            # Connect to session bus
            self.bus = dbus.SessionBus()
            
            # Get GNOME Shell screenshot interface
            shell_proxy = self.bus.get_object(
                'org.gnome.Shell',
                '/org/gnome/Shell'
            )
            self.screenshot_interface = dbus.Interface(
                shell_proxy,
                'org.gnome.Shell.Screenshot'
            )
            print("D-Bus connection to GNOME Shell established")
            
        except Exception as e:
            print(f"Failed to initialize D-Bus: {e}")
            self.bus = None
            self.screenshot_interface = None
    
    async def capture_main_display(self) -> Optional[bytes]:
        """
        Capture screenshot of the main display.
        
        Returns:
            bytes: PNG image data or None if capture failed
        """
        if not self.screenshot_interface:
            return await self._fallback_capture()
        
        try:
            # Generate unique filename
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_{timestamp}.png"
            
            # Capture screenshot using GNOME Shell D-Bus API
            success, filename = self.screenshot_interface.Screenshot(
                False,  # include_cursor
                False,  # flash
                str(screenshot_path)
            )
            
            if success and os.path.exists(screenshot_path):
                # Read screenshot data
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                
                # Clean up temp file
                try:
                    os.remove(screenshot_path)
                except OSError:
                    pass
                
                print(f"Screenshot captured successfully: {len(image_data)} bytes")
                return image_data
            else:
                print("Screenshot capture failed via D-Bus")
                return await self._fallback_capture()
                
        except Exception as e:
            print(f"Error capturing screenshot via D-Bus: {e}")
            return await self._fallback_capture()
    
    async def capture_area(self, x: int, y: int, width: int, height: int) -> Optional[bytes]:
        """
        Capture screenshot of a specific area.
        
        Args:
            x: X coordinate of top-left corner
            y: Y coordinate of top-left corner  
            width: Width of capture area
            height: Height of capture area
            
        Returns:
            bytes: PNG image data or None if capture failed
        """
        if not self.screenshot_interface:
            return await self._fallback_capture_area(x, y, width, height)
        
        try:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_area_{timestamp}.png"
            
            # Capture area using GNOME Shell D-Bus API
            success, filename = self.screenshot_interface.ScreenshotArea(
                x, y, width, height,
                False,  # flash
                str(screenshot_path)
            )
            
            if success and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                
                try:
                    os.remove(screenshot_path)
                except OSError:
                    pass
                
                return image_data
            else:
                return await self._fallback_capture_area(x, y, width, height)
                
        except Exception as e:
            print(f"Error capturing area screenshot: {e}")
            return await self._fallback_capture_area(x, y, width, height)
    
    async def capture_window(self, window_id: Optional[int] = None) -> Optional[bytes]:
        """
        Capture screenshot of a specific window.
        
        Args:
            window_id: Window ID to capture, or None for active window
            
        Returns:
            bytes: PNG image data or None if capture failed
        """
        if not self.screenshot_interface:
            return await self._fallback_capture()
        
        try:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_window_{timestamp}.png"
            
            # Capture window using GNOME Shell D-Bus API
            success, filename = self.screenshot_interface.ScreenshotWindow(
                True,   # include_frame
                False,  # include_cursor
                False,  # flash
                str(screenshot_path)
            )
            
            if success and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                
                try:
                    os.remove(screenshot_path)
                except OSError:
                    pass
                
                return image_data
            else:
                return await self._fallback_capture()
                
        except Exception as e:
            print(f"Error capturing window screenshot: {e}")
            return await self._fallback_capture()
    
    async def _fallback_capture(self) -> Optional[bytes]:
        """
        Fallback screenshot capture using grim (for wlroots compositors).
        """
        try:
            # Check if grim is available
            result = await asyncio.create_subprocess_exec(
                'which', 'grim',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode != 0:
                print("grim not found, screenshot capture unavailable")
                return None
            
            # Capture screenshot with grim
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_grim_{timestamp}.png"
            
            process = await asyncio.create_subprocess_exec(
                'grim', str(screenshot_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                
                try:
                    os.remove(screenshot_path)
                except OSError:
                    pass
                
                print(f"Screenshot captured via grim: {len(image_data)} bytes")
                return image_data
            else:
                print(f"grim capture failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Fallback screenshot capture failed: {e}")
            return None
    
    async def _fallback_capture_area(self, x: int, y: int, width: int, height: int) -> Optional[bytes]:
        """
        Fallback area capture using grim.
        """
        try:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_grim_area_{timestamp}.png"
            
            geometry = f"{x},{y} {width}x{height}"
            
            process = await asyncio.create_subprocess_exec(
                'grim', '-g', geometry, str(screenshot_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                
                try:
                    os.remove(screenshot_path)
                except OSError:
                    pass
                
                return image_data
            else:
                print(f"grim area capture failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Fallback area capture failed: {e}")
            return None
    
    def get_display_info(self) -> Tuple[int, int]:
        """
        Get display dimensions.
        
        Returns:
            Tuple[int, int]: (width, height) of primary display
        """
        try:
            # Use xrandr to get display info
            result = subprocess.run(
                ['xrandr', '--query'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'primary' in line and ' connected ' in line:
                        # Parse resolution from line like "1920x1080+0+0"
                        parts = line.split()
                        for part in parts:
                            if 'x' in part and '+' in part:
                                resolution = part.split('+')[0]
                                width, height = map(int, resolution.split('x'))
                                return width, height
            
            # Fallback to default resolution
            return 1920, 1080
            
        except Exception as e:
            print(f"Error getting display info: {e}")
            return 1920, 1080
    
    def cleanup(self):
        """Clean up temporary files and resources."""
        try:
            # Remove any remaining temp files
            for file_path in self.temp_dir.glob("screenshot_*.png"):
                try:
                    file_path.unlink()
                except OSError:
                    pass
        except Exception as e:
            print(f"Error during cleanup: {e}")