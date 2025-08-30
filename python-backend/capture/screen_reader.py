"""
Screen Reader for Horizon Overlay.
Advanced screen content extraction and analysis for context awareness.
"""

import asyncio
import subprocess
from typing import Dict, List, Optional, Tuple, NamedTuple
import re
import json
from dataclasses import dataclass
# Platform-specific screen capture import
import sys
if sys.platform == "darwin":
    from .macos_capture import MacOSScreenCapture as ScreenCapture
else:
    from .wayland_capture import WaylandScreenCapture as ScreenCapture
from .ocr_processor import OCRProcessor, OCRResult

@dataclass
class WindowInfo:
    """Information about a window."""
    title: str
    app_name: str
    window_id: int
    is_active: bool
    geometry: Tuple[int, int, int, int]  # x, y, width, height

@dataclass 
class ScreenContent:
    """Complete screen content analysis."""
    ocr_text: str
    confidence: float
    active_window: Optional[WindowInfo]
    browser_url: str
    selected_text: str
    application_context: Dict[str, any]
    timestamp: float

class ScreenReader:
    """Advanced screen content reader with application-specific parsing."""
    
    def __init__(self):
        self.screen_capture = ScreenCapture()
        self.ocr_processor = OCRProcessor()
        self.browser_patterns = {
            'chrome': [
                r'Google Chrome',
                r'Chromium',
                r'chrome'
            ],
            'firefox': [
                r'Mozilla Firefox',
                r'Firefox',
                r'firefox'
            ],
            'safari': [
                r'Safari'
            ],
            'edge': [
                r'Microsoft Edge',
                r'Edge'
            ]
        }
    
    async def read_screen_content(self, include_image: bool = True) -> ScreenContent:
        """
        Comprehensive screen content analysis.
        
        Args:
            include_image: Whether to capture and process screenshot
            
        Returns:
            ScreenContent: Complete screen analysis
        """
        import time
        timestamp = time.time()
        
        # Get active window info
        active_window = await self.get_active_window_info()
        
        # Initialize defaults
        ocr_text = ""
        confidence = 0.0
        browser_url = ""
        selected_text = ""
        app_context = {}
        
        if include_image:
            # Capture screenshot and extract text
            screenshot_data = await self.screen_capture.capture_main_display()
            if screenshot_data:
                ocr_result = await self.ocr_processor.extract_text_accurate(screenshot_data)
                ocr_text = ocr_result.text
                confidence = ocr_result.confidence
        
        # Get browser URL if applicable
        if active_window:
            browser_url = await self.extract_browser_url(active_window)
            selected_text = await self.get_selected_text()
            app_context = await self.analyze_application_context(active_window, ocr_text)
        
        return ScreenContent(
            ocr_text=ocr_text,
            confidence=confidence,
            active_window=active_window,
            browser_url=browser_url,
            selected_text=selected_text,
            application_context=app_context,
            timestamp=timestamp
        )
    
    async def get_active_window_info(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        try:
            # Use xdotool to get active window info
            result = await asyncio.create_subprocess_exec(
                'xdotool', 'getactivewindow',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return await self._fallback_window_info()
            
            window_id = int(stdout.decode().strip())
            
            # Get window title
            title_result = await asyncio.create_subprocess_exec(
                'xdotool', 'getwindowname', str(window_id),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            title_stdout, _ = await title_result.communicate()
            title = title_stdout.decode().strip() if title_result.returncode == 0 else ""
            
            # Get window geometry
            geom_result = await asyncio.create_subprocess_exec(
                'xdotool', 'getwindowgeometry', str(window_id),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            geom_stdout, _ = await geom_result.communicate()
            
            # Parse geometry (format: "Geometry: 1920x1080+0+0")
            geometry = (0, 0, 1920, 1080)  # default
            if geom_result.returncode == 0:
                geom_text = geom_stdout.decode()
                geom_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', geom_text)
                if geom_match:
                    w, h, x, y = map(int, geom_match.groups())
                    geometry = (x, y, w, h)
            
            # Extract app name from title
            app_name = self._extract_app_name(title)
            
            return WindowInfo(
                title=title,
                app_name=app_name,
                window_id=window_id,
                is_active=True,
                geometry=geometry
            )
            
        except Exception as e:
            print(f"Error getting active window info: {e}")
            return await self._fallback_window_info()
    
    async def _fallback_window_info(self) -> Optional[WindowInfo]:
        """Fallback window info using wmctrl."""
        try:
            result = await asyncio.create_subprocess_exec(
                'wmctrl', '-l',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    # Parse wmctrl output format
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        window_id = int(parts[0], 16)
                        title = parts[3]
                        app_name = self._extract_app_name(title)
                        
                        return WindowInfo(
                            title=title,
                            app_name=app_name,
                            window_id=window_id,
                            is_active=True,
                            geometry=(0, 0, 1920, 1080)
                        )
            
            return None
            
        except Exception as e:
            print(f"Fallback window info failed: {e}")
            return None
    
    def _extract_app_name(self, title: str) -> str:
        """Extract application name from window title."""
        if not title:
            return "Unknown"
        
        # Common app name patterns
        patterns = [
            r'- Google Chrome$',
            r'- Mozilla Firefox$',
            r'- Visual Studio Code$',
            r'- Terminal$',
            r'- Files$',
            r'- Settings$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, title):
                return pattern.replace('- ', '').replace('$', '')
        
        # Extract last part after dash
        parts = title.split(' - ')
        if len(parts) > 1:
            return parts[-1]
        
        return title
    
    async def extract_browser_url(self, window_info: WindowInfo) -> str:
        """Extract URL from browser window."""
        if not window_info:
            return ""
        
        app_name_lower = window_info.app_name.lower()
        title_lower = window_info.title.lower()
        
        # Check if it's a browser
        is_browser = False
        browser_type = None
        
        for browser, patterns in self.browser_patterns.items():
            for pattern in patterns:
                if re.search(pattern.lower(), title_lower) or re.search(pattern.lower(), app_name_lower):
                    is_browser = True
                    browser_type = browser
                    break
            if is_browser:
                break
        
        if not is_browser:
            return ""
        
        # Try to extract URL from window title
        url = self._extract_url_from_title(window_info.title)
        if url:
            return url
        
        # Browser-specific URL extraction methods
        if browser_type == 'chrome':
            return await self._get_chrome_url()
        elif browser_type == 'firefox':
            return await self._get_firefox_url()
        
        return ""
    
    def _extract_url_from_title(self, title: str) -> str:
        """Extract URL from browser window title."""
        # Look for URL patterns in title
        url_patterns = [
            r'https?://[^\s\)]+',
            r'www\.[^\s\)]+',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s\)]*'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, title)
            if match:
                url = match.group(0)
                # Clean up URL
                url = url.rstrip('.,!?;:')
                if not url.startswith('http'):
                    url = 'https://' + url
                return url
        
        return ""
    
    async def _get_chrome_url(self) -> str:
        """Get URL from Chrome using automation (if possible)."""
        try:
            # This is a simplified approach - in practice, you might need
            # Chrome extensions or different methods
            result = await asyncio.create_subprocess_exec(
                'xdotool', 'key', 'ctrl+l', 'ctrl+c',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            # Get clipboard content
            await asyncio.sleep(0.1)  # Brief delay
            clip_result = await asyncio.create_subprocess_exec(
                'xclip', '-selection', 'clipboard', '-o',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await clip_result.communicate()
            
            if clip_result.returncode == 0:
                url = stdout.decode().strip()
                if url.startswith('http'):
                    return url
            
        except Exception as e:
            print(f"Chrome URL extraction failed: {e}")
        
        return ""
    
    async def _get_firefox_url(self) -> str:
        """Get URL from Firefox using automation (if possible)."""
        # Similar to Chrome but with Firefox-specific methods
        return await self._get_chrome_url()  # Use same method for now
    
    async def get_selected_text(self) -> str:
        """Get currently selected text from any application."""
        try:
            # Try to get primary selection first
            result = await asyncio.create_subprocess_exec(
                'xclip', '-selection', 'primary', '-o',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                selected = stdout.decode().strip()
                if selected and len(selected) < 5000:  # Reasonable length limit
                    return selected
            
            # Fallback to clipboard
            clip_result = await asyncio.create_subprocess_exec(
                'xclip', '-selection', 'clipboard', '-o',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            clip_stdout, _ = await clip_result.communicate()
            
            if clip_result.returncode == 0:
                clipboard = clip_stdout.decode().strip()
                if clipboard and len(clipboard) < 5000:
                    return clipboard
            
        except Exception as e:
            print(f"Selected text extraction failed: {e}")
        
        return ""
    
    async def analyze_application_context(self, window_info: WindowInfo, ocr_text: str) -> Dict[str, any]:
        """Analyze application-specific context."""
        context = {
            'app_name': window_info.app_name,
            'window_title': window_info.title,
            'content_type': 'unknown'
        }
        
        app_name_lower = window_info.app_name.lower()
        
        # Code editor context
        if 'code' in app_name_lower or 'vim' in app_name_lower or 'emacs' in app_name_lower:
            context.update(await self._analyze_code_context(window_info, ocr_text))
        
        # Browser context
        elif any(browser in app_name_lower for browser in ['chrome', 'firefox', 'safari', 'edge']):
            context.update(await self._analyze_browser_context(window_info, ocr_text))
        
        # Terminal context
        elif 'terminal' in app_name_lower or 'bash' in app_name_lower:
            context.update(await self._analyze_terminal_context(ocr_text))
        
        # Document context
        elif any(app in app_name_lower for app in ['writer', 'word', 'document', 'pdf']):
            context.update(await self._analyze_document_context(ocr_text))
        
        return context
    
    async def _analyze_code_context(self, window_info: WindowInfo, ocr_text: str) -> Dict[str, any]:
        """Analyze code editor context."""
        context = {'content_type': 'code'}
        
        # Detect programming language
        if ocr_text:
            language = self._detect_programming_language(ocr_text)
            context['programming_language'] = language
        
        # Extract file path from title
        file_match = re.search(r'([^/\s]+\.[a-zA-Z0-9]+)', window_info.title)
        if file_match:
            context['file_name'] = file_match.group(1)
        
        return context
    
    async def _analyze_browser_context(self, window_info: WindowInfo, ocr_text: str) -> Dict[str, any]:
        """Analyze browser context."""
        context = {'content_type': 'web'}
        
        # Try to identify the type of web content
        if ocr_text:
            if any(keyword in ocr_text.lower() for keyword in ['github', 'git', 'repository', 'commit']):
                context['website_type'] = 'github'
            elif any(keyword in ocr_text.lower() for keyword in ['stackoverflow', 'stack overflow']):
                context['website_type'] = 'stackoverflow'
            elif any(keyword in ocr_text.lower() for keyword in ['documentation', 'docs', 'api']):
                context['website_type'] = 'documentation'
            elif any(keyword in ocr_text.lower() for keyword in ['youtube', 'video']):
                context['website_type'] = 'video'
        
        return context
    
    async def _analyze_terminal_context(self, ocr_text: str) -> Dict[str, any]:
        """Analyze terminal context."""
        context = {'content_type': 'terminal'}
        
        if ocr_text:
            # Detect common commands
            commands = re.findall(r'\$\s+(\w+)', ocr_text)
            if commands:
                context['recent_commands'] = commands[-5:]  # Last 5 commands
        
        return context
    
    async def _analyze_document_context(self, ocr_text: str) -> Dict[str, any]:
        """Analyze document context."""
        context = {'content_type': 'document'}
        
        if ocr_text:
            # Estimate reading level and content type
            word_count = len(ocr_text.split())
            context['word_count'] = word_count
            
            # Check for technical content
            technical_keywords = ['algorithm', 'implementation', 'function', 'variable', 'api', 'framework']
            if any(keyword in ocr_text.lower() for keyword in technical_keywords):
                context['document_type'] = 'technical'
        
        return context
    
    def _detect_programming_language(self, text: str) -> str:
        """Detect programming language from code text."""
        language_patterns = {
            'python': [r'def\s+\w+', r'import\s+\w+', r'from\s+\w+\s+import', r'print\s*\('],
            'javascript': [r'function\s+\w+', r'const\s+\w+', r'let\s+\w+', r'console\.log'],
            'java': [r'public\s+class', r'public\s+static\s+void\s+main', r'System\.out\.println'],
            'cpp': [r'#include\s*<', r'int\s+main\s*\(', r'std::', r'cout\s*<<'],
            'html': [r'<html>', r'<div', r'<span', r'<!DOCTYPE'],
            'css': [r'\{[^}]*\}', r'\.[\w-]+\s*\{', r'#[\w-]+\s*\{'],
            'sql': [r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'INSERT\s+INTO'],
            'bash': [r'#!/bin/bash', r'\$\w+', r'echo\s+']
        }
        
        text_lower = text.lower()
        scores = {}
        
        for language, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            scores[language] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return 'unknown'
    
    def cleanup(self):
        """Clean up resources."""
        self.screen_capture.cleanup()
        self.ocr_processor.cleanup()