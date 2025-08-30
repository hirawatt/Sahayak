"""
macOS Screenshot Capture for Horizon Overlay.
Handles screen capture on macOS using Quartz and Cocoa frameworks.
"""

import asyncio
import tempfile
import os
from typing import Optional, Tuple
from pathlib import Path
import time

try:
    from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
    from Quartz import CGDisplayCreateImage, CGMainDisplayID, CGImageDestinationCreateWithURL
    from Quartz import CGImageDestinationAddImage, CGImageDestinationFinalize
    from Cocoa import NSURL, NSScreen
    import Quartz.CoreGraphics as CG
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False
    print("macOS frameworks not available - screen capture disabled")


class MacOSScreenCapture:
    """Screen capture manager for macOS using Quartz framework."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "horizon-screenshots"
        self.temp_dir.mkdir(exist_ok=True)
        self.available = MACOS_AVAILABLE
    
    async def capture_main_display(self) -> Optional[bytes]:
        """
        Capture screenshot of the main display.
        
        Returns:
            bytes: PNG image data or None if capture failed
        """
        if not self.available:
            return await self._fallback_capture()
        
        try:
            # Get main display
            display_id = CGMainDisplayID()
            
            # Create image from display
            image = CGDisplayCreateImage(display_id)
            if not image:
                return await self._fallback_capture()
            
            # Save to temporary file
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_{timestamp}.png"
            
            # Create URL for file
            url = NSURL.fileURLWithPath_(str(screenshot_path))
            
            # Create image destination
            destination = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
            if not destination:
                return await self._fallback_capture()
            
            # Add image to destination
            CGImageDestinationAddImage(destination, image, None)
            
            # Finalize (write to file)
            success = CGImageDestinationFinalize(destination)
            
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
                return await self._fallback_capture()
                
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
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
        if not self.available:
            return await self._fallback_capture_area(x, y, width, height)
        
        try:
            # For area capture, we'll capture full screen then crop
            full_image_data = await self.capture_main_display()
            if not full_image_data:
                return None
            
            # Use PIL to crop the image
            from PIL import Image
            import io
            
            # Load image from bytes
            image = Image.open(io.BytesIO(full_image_data))
            
            # Crop to specified area
            cropped = image.crop((x, y, x + width, y + height))
            
            # Convert back to bytes
            output = io.BytesIO()
            cropped.save(output, format='PNG')
            return output.getvalue()
            
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
        # For now, just capture main display
        # Window-specific capture would require more complex Quartz API usage
        return await self.capture_main_display()
    
    async def _fallback_capture(self) -> Optional[bytes]:
        """
        Fallback screenshot capture using screencapture command.
        """
        try:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_fallback_{timestamp}.png"
            
            process = await asyncio.create_subprocess_exec(
                'screencapture', '-x', str(screenshot_path),
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
                
                print(f"Screenshot captured via screencapture: {len(image_data)} bytes")
                return image_data
            else:
                print(f"screencapture failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Fallback screenshot capture failed: {e}")
            return None
    
    async def _fallback_capture_area(self, x: int, y: int, width: int, height: int) -> Optional[bytes]:
        """
        Fallback area capture using screencapture command.
        """
        try:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.temp_dir / f"screenshot_area_{timestamp}.png"
            
            # screencapture area format: -R x,y,width,height
            area = f"{x},{y},{width},{height}"
            
            process = await asyncio.create_subprocess_exec(
                'screencapture', '-x', '-R', area, str(screenshot_path),
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
                print(f"screencapture area failed: {stderr.decode()}")
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
            if self.available:
                # Use NSScreen to get display info
                main_screen = NSScreen.mainScreen()
                if main_screen:
                    frame = main_screen.frame()
                    return int(frame.size.width), int(frame.size.height)
            
            # Fallback to system_profiler
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse resolution from output
                for line in result.stdout.split('\n'):
                    if 'Resolution:' in line:
                        # Extract resolution like "1920 x 1080"
                        parts = line.split(':')[1].strip().split(' x ')
                        if len(parts) == 2:
                            width = int(parts[0].strip())
                            height = int(parts[1].strip())
                            return width, height
            
            # Final fallback
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


# Alias for compatibility
WaylandScreenCapture = MacOSScreenCapture