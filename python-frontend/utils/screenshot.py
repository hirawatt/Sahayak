"""
Screenshot capture using pydbus for D-Bus integration
"""

import logging
import asyncio
from typing import Optional, Tuple
from pathlib import Path
import tempfile
from datetime import datetime

try:
    from pydbus import SessionBus
    PYDBUS_AVAILABLE = True
except ImportError:
    PYDBUS_AVAILABLE = False
    import subprocess

from PIL import Image
import numpy as np


class ScreenshotManager:
    """Manages screenshot capture using D-Bus services"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bus = None
        self.screenshot_service = None
        
        if PYDBUS_AVAILABLE:
            try:
                self.bus = SessionBus()
                # Try GNOME Shell screenshot service first
                self._init_gnome_service()
            except Exception as e:
                self.logger.warning(f"Failed to initialize D-Bus screenshot service: {e}")
                self.bus = None
    
    def _init_gnome_service(self):
        """Initialize GNOME Shell screenshot service"""
        try:
            self.screenshot_service = self.bus.get(
                'org.gnome.Shell.Screenshot',
                '/org/gnome/Shell/Screenshot'
            )
            self.logger.info("Connected to GNOME Shell screenshot service")
        except Exception as e:
            self.logger.debug(f"GNOME Shell screenshot not available: {e}")
            self.screenshot_service = None
    
    async def capture_screen(self, save_path: Optional[str] = None) -> Optional[str]:
        """Capture full screen screenshot"""
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"/tmp/horizon_screenshot_{timestamp}.png"
        
        try:
            if self.screenshot_service:
                # Use GNOME Shell D-Bus service
                success, filename = self.screenshot_service.Screenshot(
                    False,  # include_cursor
                    False,  # flash
                    save_path
                )
                if success:
                    self.logger.debug(f"Screenshot saved to: {filename}")
                    return filename
            
            # Fallback to command line tools
            return await self._fallback_screenshot(save_path)
            
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    async def capture_window(self, window_id: Optional[str] = None, save_path: Optional[str] = None) -> Optional[str]:
        """Capture specific window screenshot"""
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"/tmp/horizon_window_{timestamp}.png"
        
        try:
            if self.screenshot_service and window_id:
                # Use GNOME Shell service for window capture
                success, filename = self.screenshot_service.ScreenshotWindow(
                    int(window_id),
                    False,  # include_cursor
                    False,  # flash
                    save_path
                )
                if success:
                    return filename
            
            # Fallback to command line
            return await self._fallback_window_screenshot(window_id, save_path)
            
        except Exception as e:
            self.logger.error(f"Failed to capture window screenshot: {e}")
            return None
    
    async def capture_area(self, x: int, y: int, width: int, height: int, save_path: Optional[str] = None) -> Optional[str]:
        """Capture specific area screenshot"""
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"/tmp/horizon_area_{timestamp}.png"
        
        try:
            if self.screenshot_service:
                success, filename = self.screenshot_service.ScreenshotArea(
                    x, y, width, height,
                    False,  # flash
                    save_path
                )
                if success:
                    return filename
            
            # Fallback using ImageMagick or gnome-screenshot
            return await self._fallback_area_screenshot(x, y, width, height, save_path)
            
        except Exception as e:
            self.logger.error(f"Failed to capture area screenshot: {e}")
            return None
    
    async def _fallback_screenshot(self, save_path: str) -> Optional[str]:
        """Fallback screenshot using command line tools"""
        commands = [
            ['gnome-screenshot', '-f', save_path],
            ['import', save_path],  # ImageMagick
            ['scrot', save_path],
            ['maim', save_path]
        ]
        
        for cmd in commands:
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode == 0 and Path(save_path).exists():
                    self.logger.debug(f"Screenshot captured using {cmd[0]}")
                    return save_path
                    
            except FileNotFoundError:
                continue
            except Exception as e:
                self.logger.debug(f"Command {cmd[0]} failed: {e}")
                continue
        
        self.logger.error("No screenshot tool available")
        return None
    
    async def _fallback_window_screenshot(self, window_id: Optional[str], save_path: str) -> Optional[str]:
        """Fallback window screenshot"""
        if not window_id:
            return await self._fallback_screenshot(save_path)
        
        commands = [
            ['gnome-screenshot', '-w', '-f', save_path],
            ['import', '-window', window_id, save_path],
            ['scrot', '-s', save_path]
        ]
        
        for cmd in commands:
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode == 0:
                    return save_path
                    
            except FileNotFoundError:
                continue
            except Exception as e:
                self.logger.debug(f"Command {cmd[0]} failed: {e}")
                continue
        
        return None
    
    async def _fallback_area_screenshot(self, x: int, y: int, width: int, height: int, save_path: str) -> Optional[str]:
        """Fallback area screenshot"""
        commands = [
            ['import', '-window', 'root', '-crop', f'{width}x{height}+{x}+{y}', save_path],
            ['maim', '-g', f'{width}x{height}+{x}+{y}', save_path]
        ]
        
        for cmd in commands:
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode == 0:
                    return save_path
                    
            except FileNotFoundError:
                continue
            except Exception as e:
                self.logger.debug(f"Command {cmd[0]} failed: {e}")
                continue
        
        return None
    
    def get_image_data(self, image_path: str) -> Optional[np.ndarray]:
        """Load image as numpy array for processing"""
        try:
            image = Image.open(image_path)
            return np.array(image)
        except Exception as e:
            self.logger.error(f"Failed to load image {image_path}: {e}")
            return None
    
    async def get_active_window_id(self) -> Optional[str]:
        """Get the ID of the currently active window"""
        try:
            # Try using xdotool first
            process = await asyncio.create_subprocess_exec(
                'xdotool', 'getactivewindow',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            
            # Fallback to xprop
            process = await asyncio.create_subprocess_exec(
                'xprop', '-root', '_NET_ACTIVE_WINDOW',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                # Parse xprop output
                output = stdout.decode().strip()
                if 'window id #' in output:
                    window_id = output.split('window id # ')[-1].split(',')[0]
                    return window_id
            
        except Exception as e:
            self.logger.debug(f"Failed to get active window ID: {e}")
        
        return None