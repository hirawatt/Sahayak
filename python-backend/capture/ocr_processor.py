"""
OCR Processor for Horizon Overlay.
Handles text extraction from screenshots using pytesseract.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
from typing import Optional, List, Dict, Tuple, NamedTuple
import asyncio
import concurrent.futures
import threading
import re

class OCRResult(NamedTuple):
    """OCR result with text and confidence."""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)

class TextBlock(NamedTuple):
    """Text block with position and formatting info."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    font_size: Optional[int] = None

class OCRProcessor:
    """Advanced OCR processor with preprocessing and optimization."""
    
    def __init__(self, language: str = 'eng'):
        self.language = language
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._verify_tesseract()
    
    def _verify_tesseract(self):
        """Verify tesseract installation and language support."""
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract version: {version}")
            
            # Check if specified language is available
            languages = pytesseract.get_languages()
            if self.language not in languages:
                print(f"Warning: Language '{self.language}' not found. Available: {languages}")
                self.language = 'eng'  # Fallback to English
                
        except Exception as e:
            print(f"Tesseract verification failed: {e}")
            print("Please install tesseract-ocr: sudo apt install tesseract-ocr")
    
    async def extract_text(self, image_data: bytes, 
                          preprocess: bool = True,
                          extract_blocks: bool = False) -> OCRResult:
        """
        Extract text from image data.
        
        Args:
            image_data: Raw image bytes (PNG/JPEG)
            preprocess: Whether to apply image preprocessing
            extract_blocks: Whether to extract individual text blocks
            
        Returns:
            OCRResult: Extracted text with confidence score
        """
        try:
            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._process_image,
                image_data,
                preprocess,
                extract_blocks
            )
            return result
            
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            return OCRResult(text="", confidence=0.0)
    
    def _process_image(self, image_data: bytes, 
                      preprocess: bool,
                      extract_blocks: bool) -> OCRResult:
        """Process image and extract text (runs in thread pool)."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to OpenCV format for preprocessing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            if preprocess:
                cv_image = self._preprocess_image(cv_image)
            
            # Convert back to PIL for tesseract
            processed_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Configure tesseract
            config = self._get_tesseract_config()
            
            # Extract text with confidence
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.language,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Process results
            text_blocks = self._parse_tesseract_data(data)
            
            if extract_blocks:
                # Return structured text blocks
                combined_text = self._combine_text_blocks(text_blocks)
            else:
                # Simple text extraction
                text = pytesseract.image_to_string(
                    processed_image,
                    lang=self.language,
                    config=config
                )
                combined_text = self._clean_text(text)
            
            # Calculate average confidence
            confidences = [block.confidence for block in text_blocks if block.confidence > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return OCRResult(
                text=combined_text,
                confidence=avg_confidence / 100.0  # Convert to 0-1 range
            )
            
        except Exception as e:
            print(f"Error processing image for OCR: {e}")
            return OCRResult(text="", confidence=0.0)
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Apply preprocessing to improve OCR accuracy.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            np.ndarray: Preprocessed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (1, 1), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to BGR for consistency
        return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
    
    def _get_tesseract_config(self) -> str:
        """Get optimized tesseract configuration."""
        # PSM (Page Segmentation Mode) options:
        # 3: Fully automatic page segmentation, but no OSD
        # 6: Assume a single uniform block of text
        # 8: Treat the image as a single word
        # 11: Treat the image as a single text line
        # 13: Raw line. Treat the image as a single text line, bypassing hacks
        
        return '--psm 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:()[]{}"\'-+=/*@#$%^&_|\\~`<> '
    
    def _parse_tesseract_data(self, data: Dict) -> List[TextBlock]:
        """Parse tesseract output data into text blocks."""
        text_blocks = []
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            confidence = float(data['conf'][i])
            
            # Skip empty text or very low confidence
            if not text or confidence < 30:
                continue
            
            # Extract bounding box
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            
            text_blocks.append(TextBlock(
                text=text,
                x=x,
                y=y,
                width=w,
                height=h,
                confidence=confidence,
                font_size=h  # Approximate font size from height
            ))
        
        return text_blocks
    
    def _combine_text_blocks(self, blocks: List[TextBlock]) -> str:
        """Combine text blocks into coherent text with proper spacing."""
        if not blocks:
            return ""
        
        # Sort blocks by y-coordinate (top to bottom), then x-coordinate (left to right)
        sorted_blocks = sorted(blocks, key=lambda b: (b.y, b.x))
        
        lines = []
        current_line = []
        current_y = sorted_blocks[0].y
        line_threshold = 10  # Pixels tolerance for same line
        
        for block in sorted_blocks:
            # Check if this block is on the same line
            if abs(block.y - current_y) <= line_threshold:
                current_line.append(block)
            else:
                # New line detected
                if current_line:
                    line_text = self._combine_line_blocks(current_line)
                    if line_text.strip():
                        lines.append(line_text)
                
                current_line = [block]
                current_y = block.y
        
        # Don't forget the last line
        if current_line:
            line_text = self._combine_line_blocks(current_line)
            if line_text.strip():
                lines.append(line_text)
        
        # Join lines with newlines
        combined_text = '\n'.join(lines)
        return self._clean_text(combined_text)
    
    def _combine_line_blocks(self, line_blocks: List[TextBlock]) -> str:
        """Combine blocks that are on the same line."""
        if not line_blocks:
            return ""
        
        # Sort by x-coordinate (left to right)
        sorted_blocks = sorted(line_blocks, key=lambda b: b.x)
        
        words = []
        prev_x_end = 0
        
        for block in sorted_blocks:
            # Add space if there's a gap between words
            if prev_x_end > 0 and block.x > prev_x_end + 5:
                words.append(' ')
            
            words.append(block.text)
            prev_x_end = block.x + block.width
        
        return ''.join(words)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # Fix common OCR errors
        replacements = {
            '|': 'I',  # Common OCR mistake
            '0': 'O',  # In some contexts
            '5': 'S',  # In some contexts
        }
        
        # Apply replacements cautiously (only for single characters surrounded by letters)
        for old, new in replacements.items():
            pattern = r'(?<=[a-zA-Z])' + re.escape(old) + r'(?=[a-zA-Z])'
            cleaned = re.sub(pattern, new, cleaned)
        
        return cleaned
    
    async def extract_text_fast(self, image_data: bytes) -> str:
        """
        Fast text extraction with minimal preprocessing.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            str: Extracted text
        """
        result = await self.extract_text(image_data, preprocess=False, extract_blocks=False)
        return result.text
    
    async def extract_text_accurate(self, image_data: bytes) -> OCRResult:
        """
        Accurate text extraction with full preprocessing.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            OCRResult: Detailed extraction result
        """
        return await self.extract_text(image_data, preprocess=True, extract_blocks=True)
    
    def cleanup(self):
        """Clean up thread pool resources."""
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)