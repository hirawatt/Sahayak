"""
AI Context Manager - Python equivalent of AIContextManager.swift
Handles screen capture, OCR, selected text, and browser URL detection (cross-platform)
"""

import asyncio
import subprocess
import sys
from typing import Optional, Dict, Any
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import base64

# Platform-specific imports
if sys.platform == "darwin":
    from capture.macos_capture import MacOSScreenCapture as ScreenCapture
else:
    try:
        import dbus
        from capture.wayland_capture import WaylandScreenCapture as ScreenCapture
    except ImportError:
        print("D-Bus not available - using fallback screen capture")
        from capture.macos_capture import MacOSScreenCapture as ScreenCapture

from models.context_data import ContextData


class AIContextManager:
    """Manages the capture of contextual information from screen and system - Ubuntu/Wayland version"""
    
    def __init__(self):
        self.selected_text: str = ""
        self.ocr_text: str = ""
        self.image_bytes: Optional[bytes] = None
        self.browser_url: str = ""
        self.did_change_selected_text: bool = False
        
        # Initialize screen capture
        self.screen_capture = ScreenCapture()
        
    async def capture_current_context(self, capture_image: bool = True) -> ContextData:
        """
        Main context capture method - equivalent to Swift captureCurrentContext
        
        Args:
            capture_image: Whether to capture and store screenshot data
            
        Returns:
            ContextData: Captured context information
        """
        # Capture selected text
        selected = await self.capture_selected_text()
        self.selected_text = selected
        
        # Capture browser URL
        browser_url = await self.get_active_browser_url()
        self.browser_url = browser_url
        
        # Capture screenshot and perform OCR
        if capture_image:
            screenshot_data = await self.capture_screenshot()
            if screenshot_data:
                self.image_bytes = screenshot_data
                
                # Perform OCR on screenshot
                ocr_results = await self.perform_ocr(screenshot_data)
                self.ocr_text = ocr_results
            else:
                self.image_bytes = None
                self.ocr_text = ""
        else:
            # Still perform OCR even if not storing image
            screenshot_data = await self.capture_screenshot()
            if screenshot_data:
                ocr_results = await self.perform_ocr(screenshot_data)
                self.ocr_text = ocr_results
            else:
                self.ocr_text = ""
        
        return ContextData(
            selected_text=self.selected_text,
            ocr_text=self.ocr_text,
            browser_url=self.browser_url,
            image_data=self.image_bytes if capture_image else None
        )
    
    async def capture_selected_text(self) -> str:
        """
        Capture currently selected text using clipboard - Ubuntu equivalent
        """
        try:
            # Get current clipboard content
            result = subprocess.run(
                ["xclip", "-selection", "primary", "-o"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                selected_text = result.stdout.strip()
                self.did_change_selected_text = True
                return selected_text
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to regular clipboard if primary selection fails
            try:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except:
                pass
        
        self.did_change_selected_text = True
        return ""
    
    async def capture_screenshot(self) -> Optional[bytes]:
        """
        Capture screenshot using Wayland GNOME Screenshot API
        """
        try:
            return await self.screen_capture.capture_main_display()
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
            return None
    
    async def perform_ocr(self, image_data: bytes) -> str:
        """
        Perform OCR on image data using pytesseract
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            str: Extracted text from image
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to OpenCV format for preprocessing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get better OCR results
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Perform OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(thresh, config=custom_config)
            
            # Clean up the text
            cleaned_text = ' '.join(text.split())
            return cleaned_text
            
        except Exception as e:
            print(f"OCR processing failed: {e}")
            return ""
    
    async def get_active_browser_url(self) -> str:
        """
        Get URL from active browser tab - Ubuntu equivalent using window title parsing
        """
        try:
            # Try to get active window title
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                window_title = result.stdout.strip()
                
                # Parse URL from common browser title formats
                url = self._extract_url_from_title(window_title)
                return url
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return ""
    
    def _extract_url_from_title(self, title: str) -> str:
        """
        Extract URL from browser window title
        
        Args:
            title: Browser window title
            
        Returns:
            str: Extracted URL or empty string
        """
        # Common browser title patterns
        patterns = [
            # Chrome/Chromium: "Page Title - Google Chrome"
            # Firefox: "Page Title - Mozilla Firefox" 
            # Extract domain from title if it contains URL-like patterns
        ]
        
        # Simple heuristic: look for domain patterns in title
        import re
        url_pattern = r'https?://([^\s]+)'
        match = re.search(url_pattern, title)
        if match:
            return match.group(1)
        
        # Look for domain-like patterns
        domain_pattern = r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
        match = re.search(domain_pattern, title)
        if match:
            return match.group(0)
        
        return ""