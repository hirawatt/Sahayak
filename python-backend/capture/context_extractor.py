"""
Context Extractor for Horizon Overlay.
Intelligent context analysis and extraction for AI assistance.
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from .screen_reader import ScreenReader, ScreenContent
# Platform-specific screen capture import
import sys
if sys.platform == "darwin":
    from .macos_capture import MacOSScreenCapture as ScreenCapture
else:
    from .wayland_capture import WaylandScreenCapture as ScreenCapture
from .ocr_processor import OCRProcessor

@dataclass
class ContextItem:
    """Individual piece of context information."""
    type: str  # 'text', 'url', 'code', 'command', etc.
    content: str
    confidence: float
    source: str  # 'ocr', 'clipboard', 'window_title', etc.
    metadata: Dict[str, Any]

@dataclass
class ExtractedContext:
    """Complete extracted context with analysis."""
    items: List[ContextItem]
    primary_content: str
    content_type: str
    application_context: Dict[str, Any]
    timestamp: datetime
    confidence_score: float

class ContextExtractor:
    """Intelligent context extraction and analysis."""
    
    def __init__(self):
        self.screen_reader = ScreenReader()
        self.screen_capture = ScreenCapture()
        self.ocr_processor = OCRProcessor()
        
        # Context extraction patterns
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'file_path': r'(?:/[^/\s]+)+/?|[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*',
            'code_function': r'\b\w+\s*\([^)]*\)\s*\{?',
            'error_message': r'(?i)error|exception|failed|invalid|cannot|unable|denied',
            'command_line': r'\$\s+[\w\-\.\/]+(?:\s+[\w\-\.\/]+)*',
            'json_data': r'\{[^{}]*\}',
            'api_endpoint': r'/api/v?\d*/[\w/]+',
            'version_number': r'v?\d+\.\d+(?:\.\d+)?',
            'hash_id': r'\b[a-f0-9]{6,40}\b',
            'datetime': r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}'
        }
    
    async def extract_context(self, capture_image: bool = True, 
                            analyze_deep: bool = False) -> ExtractedContext:
        """
        Extract comprehensive context from current screen state.
        
        Args:
            capture_image: Whether to capture and analyze screenshot
            analyze_deep: Whether to perform deep content analysis
            
        Returns:
            ExtractedContext: Complete context analysis
        """
        # Get screen content
        screen_content = await self.screen_reader.read_screen_content(capture_image)
        
        # Extract context items
        context_items = []
        
        # Extract from OCR text
        if screen_content.ocr_text:
            ocr_items = await self._extract_from_text(
                screen_content.ocr_text, 
                'ocr', 
                screen_content.confidence
            )
            context_items.extend(ocr_items)
        
        # Extract from selected text
        if screen_content.selected_text:
            selected_items = await self._extract_from_text(
                screen_content.selected_text,
                'selection',
                1.0  # High confidence for selected text
            )
            context_items.extend(selected_items)
        
        # Extract from browser URL
        if screen_content.browser_url:
            url_item = ContextItem(
                type='url',
                content=screen_content.browser_url,
                confidence=0.9,
                source='browser',
                metadata={'is_active_tab': True}
            )
            context_items.append(url_item)
        
        # Extract from window title
        if screen_content.active_window:
            title_items = await self._extract_from_text(
                screen_content.active_window.title,
                'window_title',
                0.8
            )
            context_items.extend(title_items)
        
        # Determine primary content and type
        primary_content = self._determine_primary_content(context_items, screen_content)
        content_type = self._determine_content_type(screen_content, context_items)
        
        # Calculate overall confidence
        confidence_score = self._calculate_confidence(context_items, screen_content)
        
        # Perform deep analysis if requested
        if analyze_deep:
            context_items = await self._perform_deep_analysis(context_items, screen_content)
        
        return ExtractedContext(
            items=context_items,
            primary_content=primary_content,
            content_type=content_type,
            application_context=screen_content.application_context,
            timestamp=datetime.now(),
            confidence_score=confidence_score
        )
    
    async def _extract_from_text(self, text: str, source: str, 
                               base_confidence: float) -> List[ContextItem]:
        """Extract context items from text using pattern matching."""
        items = []
        
        for pattern_name, pattern in self.patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                content = match.group(0).strip()
                if not content or len(content) < 3:
                    continue
                
                # Calculate confidence based on pattern and source
                confidence = base_confidence * self._get_pattern_confidence(pattern_name, content)
                
                # Extract metadata
                metadata = self._extract_pattern_metadata(pattern_name, content, match, text)
                
                item = ContextItem(
                    type=pattern_name,
                    content=content,
                    confidence=confidence,
                    source=source,
                    metadata=metadata
                )
                items.append(item)
        
        # Extract natural language context
        nl_items = await self._extract_natural_language_context(text, source, base_confidence)
        items.extend(nl_items)
        
        return items
    
    def _get_pattern_confidence(self, pattern_name: str, content: str) -> float:
        """Get confidence multiplier for different pattern types."""
        confidence_map = {
            'email': 0.95,
            'url': 0.9,
            'phone': 0.85,
            'ip_address': 0.9,
            'file_path': 0.8,
            'code_function': 0.7,
            'error_message': 0.8,
            'command_line': 0.85,
            'json_data': 0.75,
            'api_endpoint': 0.8,
            'version_number': 0.7,
            'hash_id': 0.6,
            'datetime': 0.85
        }
        
        base_confidence = confidence_map.get(pattern_name, 0.5)
        
        # Adjust based on content characteristics
        if len(content) > 100:
            base_confidence *= 0.8  # Long matches might be false positives
        elif len(content) < 5:
            base_confidence *= 0.6  # Very short matches are less reliable
        
        return min(base_confidence, 1.0)
    
    def _extract_pattern_metadata(self, pattern_name: str, content: str, 
                                 match: re.Match, full_text: str) -> Dict[str, Any]:
        """Extract metadata for specific pattern types."""
        metadata = {
            'start_pos': match.start(),
            'end_pos': match.end(),
            'length': len(content)
        }
        
        if pattern_name == 'url':
            metadata.update(self._analyze_url(content))
        elif pattern_name == 'email':
            metadata.update(self._analyze_email(content))
        elif pattern_name == 'file_path':
            metadata.update(self._analyze_file_path(content))
        elif pattern_name == 'code_function':
            metadata.update(self._analyze_code_function(content))
        elif pattern_name == 'error_message':
            metadata.update(self._analyze_error_context(content, full_text))
        
        return metadata
    
    def _analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze URL for additional context."""
        import urllib.parse
        
        try:
            parsed = urllib.parse.urlparse(url)
            return {
                'domain': parsed.netloc,
                'path': parsed.path,
                'scheme': parsed.scheme,
                'has_query': bool(parsed.query),
                'is_api': '/api/' in parsed.path.lower(),
                'is_documentation': any(word in parsed.path.lower() 
                                      for word in ['docs', 'documentation', 'help'])
            }
        except:
            return {'is_valid': False}
    
    def _analyze_email(self, email: str) -> Dict[str, Any]:
        """Analyze email for additional context."""
        parts = email.split('@')
        if len(parts) == 2:
            return {
                'username': parts[0],
                'domain': parts[1],
                'is_business': any(domain in parts[1].lower() 
                                 for domain in ['company', 'corp', 'inc', 'ltd'])
            }
        return {}
    
    def _analyze_file_path(self, path: str) -> Dict[str, Any]:
        """Analyze file path for additional context."""
        import os
        
        metadata = {
            'filename': os.path.basename(path),
            'directory': os.path.dirname(path),
            'is_absolute': os.path.isabs(path)
        }
        
        # Detect file type
        if '.' in metadata['filename']:
            extension = metadata['filename'].split('.')[-1].lower()
            metadata['extension'] = extension
            metadata['file_type'] = self._classify_file_type(extension)
        
        return metadata
    
    def _classify_file_type(self, extension: str) -> str:
        """Classify file type based on extension."""
        type_map = {
            'py': 'python',
            'js': 'javascript',
            'html': 'web',
            'css': 'web',
            'json': 'data',
            'xml': 'data',
            'csv': 'data',
            'txt': 'text',
            'md': 'documentation',
            'pdf': 'document',
            'doc': 'document',
            'docx': 'document',
            'jpg': 'image',
            'png': 'image',
            'gif': 'image',
            'mp4': 'video',
            'mp3': 'audio'
        }
        return type_map.get(extension, 'unknown')
    
    def _analyze_code_function(self, function: str) -> Dict[str, Any]:
        """Analyze code function for additional context."""
        # Extract function name
        func_match = re.match(r'(\w+)\s*\(', function)
        if func_match:
            func_name = func_match.group(1)
            return {
                'function_name': func_name,
                'has_parameters': '(' in function and ')' in function,
                'is_constructor': func_name[0].isupper(),
                'language_hints': self._detect_language_from_function(function)
            }
        return {}
    
    def _detect_language_from_function(self, function: str) -> List[str]:
        """Detect programming language hints from function syntax."""
        hints = []
        
        if 'def ' in function:
            hints.append('python')
        if 'function ' in function:
            hints.append('javascript')
        if 'public ' in function or 'private ' in function:
            hints.append('java')
        if '::' in function:
            hints.append('cpp')
        
        return hints
    
    def _analyze_error_context(self, error: str, full_text: str) -> Dict[str, Any]:
        """Analyze error message context."""
        # Look for error codes, line numbers, stack traces
        line_number = re.search(r'line\s+(\d+)', full_text, re.IGNORECASE)
        error_code = re.search(r'error\s*:?\s*(\d+)', error, re.IGNORECASE)
        
        return {
            'has_line_number': line_number is not None,
            'line_number': int(line_number.group(1)) if line_number else None,
            'has_error_code': error_code is not None,
            'error_code': error_code.group(1) if error_code else None,
            'severity': self._classify_error_severity(error)
        }
    
    def _classify_error_severity(self, error: str) -> str:
        """Classify error severity level."""
        error_lower = error.lower()
        
        if any(word in error_lower for word in ['fatal', 'critical', 'emergency']):
            return 'critical'
        elif any(word in error_lower for word in ['error', 'failed', 'exception']):
            return 'error'
        elif any(word in error_lower for word in ['warning', 'warn']):
            return 'warning'
        elif any(word in error_lower for word in ['info', 'notice']):
            return 'info'
        else:
            return 'unknown'
    
    async def _extract_natural_language_context(self, text: str, source: str, 
                                               base_confidence: float) -> List[ContextItem]:
        """Extract natural language context like questions, statements, etc."""
        items = []
        
        # Extract questions
        questions = re.findall(r'[.!?]\s*([^.!?]*\?)', text)
        for question in questions:
            if len(question.strip()) > 10:
                items.append(ContextItem(
                    type='question',
                    content=question.strip(),
                    confidence=base_confidence * 0.7,
                    source=source,
                    metadata={'is_question': True}
                ))
        
        # Extract key phrases (simple heuristic)
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if 20 <= len(sentence) <= 200:  # Reasonable sentence length
                # Check if it's a meaningful sentence
                if self._is_meaningful_sentence(sentence):
                    items.append(ContextItem(
                        type='statement',
                        content=sentence,
                        confidence=base_confidence * 0.6,
                        source=source,
                        metadata={'word_count': len(sentence.split())}
                    ))
        
        return items
    
    def _is_meaningful_sentence(self, sentence: str) -> bool:
        """Determine if a sentence contains meaningful content."""
        # Simple heuristics for meaningful content
        word_count = len(sentence.split())
        
        # Must have reasonable word count
        if word_count < 3 or word_count > 50:
            return False
        
        # Must contain some common English words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = set(word.lower() for word in sentence.split())
        
        if not words.intersection(common_words):
            return False
        
        # Must not be mostly numbers or special characters
        alpha_ratio = sum(1 for char in sentence if char.isalpha()) / len(sentence)
        if alpha_ratio < 0.6:
            return False
        
        return True
    
    def _determine_primary_content(self, items: List[ContextItem], 
                                 screen_content: ScreenContent) -> str:
        """Determine the primary content from extracted items."""
        # Prioritize selected text
        if screen_content.selected_text:
            return screen_content.selected_text
        
        # Find highest confidence item
        if items:
            best_item = max(items, key=lambda x: x.confidence)
            if best_item.confidence > 0.7:
                return best_item.content
        
        # Fallback to OCR text summary
        if screen_content.ocr_text:
            words = screen_content.ocr_text.split()
            if len(words) > 50:
                # Return first 50 words as summary
                return ' '.join(words[:50]) + '...'
            return screen_content.ocr_text
        
        return ""
    
    def _determine_content_type(self, screen_content: ScreenContent, 
                               items: List[ContextItem]) -> str:
        """Determine the primary content type."""
        # Check application context first
        if screen_content.application_context:
            app_content_type = screen_content.application_context.get('content_type')
            if app_content_type and app_content_type != 'unknown':
                return app_content_type
        
        # Analyze extracted items
        type_counts = {}
        for item in items:
            if item.confidence > 0.5:
                type_counts[item.type] = type_counts.get(item.type, 0) + 1
        
        if type_counts:
            return max(type_counts.items(), key=lambda x: x[1])[0]
        
        return 'general'
    
    def _calculate_confidence(self, items: List[ContextItem], 
                            screen_content: ScreenContent) -> float:
        """Calculate overall confidence score."""
        if not items:
            return screen_content.confidence
        
        # Weight by item confidence and count
        total_confidence = sum(item.confidence for item in items)
        item_count = len(items)
        
        # Normalize and combine with OCR confidence
        item_confidence = total_confidence / item_count if item_count > 0 else 0
        combined_confidence = (item_confidence + screen_content.confidence) / 2
        
        return min(combined_confidence, 1.0)
    
    async def _perform_deep_analysis(self, items: List[ContextItem], 
                                   screen_content: ScreenContent) -> List[ContextItem]:
        """Perform deep analysis on extracted context."""
        # This could include:
        # - Sentiment analysis
        # - Entity recognition
        # - Intent detection
        # - Relationship extraction
        
        # For now, just add some basic analysis
        for item in items:
            if item.type == 'statement':
                # Add sentiment analysis placeholder
                item.metadata['sentiment'] = self._simple_sentiment_analysis(item.content)
            elif item.type == 'question':
                # Add question type analysis
                item.metadata['question_type'] = self._classify_question_type(item.content)
        
        return items
    
    def _simple_sentiment_analysis(self, text: str) -> str:
        """Simple sentiment analysis."""
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic'}
        negative_words = {'bad', 'terrible', 'awful', 'horrible', 'wrong', 'error', 'failed'}
        
        words = set(word.lower() for word in text.split())
        
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question."""
        question_lower = question.lower()
        
        if question_lower.startswith(('what', 'which')):
            return 'what'
        elif question_lower.startswith(('how', 'when')):
            return 'how'
        elif question_lower.startswith(('why', 'where')):
            return 'why'
        elif question_lower.startswith(('who', 'whom')):
            return 'who'
        elif question_lower.startswith(('is', 'are', 'can', 'could', 'should', 'would')):
            return 'yes_no'
        else:
            return 'other'
    
    def to_dict(self, context: ExtractedContext) -> Dict[str, Any]:
        """Convert extracted context to dictionary for API responses."""
        return {
            'items': [asdict(item) for item in context.items],
            'primary_content': context.primary_content,
            'content_type': context.content_type,
            'application_context': context.application_context,
            'timestamp': context.timestamp.isoformat(),
            'confidence_score': context.confidence_score,
            'summary': {
                'total_items': len(context.items),
                'high_confidence_items': len([i for i in context.items if i.confidence > 0.8]),
                'content_types': list(set(i.type for i in context.items))
            }
        }
    
    def cleanup(self):
        """Clean up resources."""
        self.screen_reader.cleanup()