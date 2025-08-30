"""
Wayland Screenshot Utility - Ubuntu/Wayland screen capture using GNOME Shell API
"""

import asyncio
import subprocess
import tempfile
import os
from typing import Optional
import dbus
from pydbus import SessionBus


class WaylandScreenCapture:
    """Handles screen capture for Wayland using GNOME Shell Screenshot API"""
    
    def __init__(self):
        self.session_bus = None
        self.screenshot_interface = None
        
    async def initialize(self):
        """Initialize D-Bus connection to GNOME Shell"""
        try:
            self.session_bus = SessionBus()
            self.screenshot_interface = self.session_bus.get(
                'org.gnome.Shell',
                '/org/gnome/Shell/Screenshot'
            )
            return True
        except Exception as e:
            print(f"Failed to initialize Wayland screen capture: {e}")
            return False
    
    async def capture_main_display(self) -> Optional[bytes]:
        """
        Capture screenshot of main display
        
        Returns:
            bytes: PNG image data or None if capture failed
        """
        try:
            # Initialize if not already done
            if not self.screenshot_interface:
                if not await self.initialize():
                    return await self._fallback_capture()
            
            # Create temporary file for screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Call GNOME Shell Screenshot API
                result = self.screenshot_interface.Screenshot(
                    True,  # include_cursor
                    False,  # flash
                    temp_path
                )
                
                if result:
                    # Read the captured image
                    with open(temp_path, 'rb') as f:
                        image_data = f.read()
                    
                    return image_data
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
        except Exception as e:
            print(f"GNOME Shell screenshot failed: {e}")
            return await self._fallback_capture()
        
        return None
    
    async def _fallback_capture(self) -> Optional[bytes]:
        """
        Fallback screen capture using grim (if available)
        """
        try:
            # Try using grim for wlroots-based compositors
            result = subprocess.run(
                ['grim', '-'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        try:
            # Last resort: try ImageMagick import
            result = subprocess.run(
                ['import', '-window', 'root', 'png:-'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        print("All screen capture methods failed")
        return None