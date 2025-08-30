"""
Data models for context information - Python equivalent of Swift models
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ContextData:
    """Main context data structure"""
    selected_text: str
    ocr_text: str
    browser_url: str
    image_data: Optional[bytes] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Note:
    """Note model - equivalent to Note.swift"""
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    uniqueid: str
    
    def __post_init__(self):
        if not self.uniqueid:
            import uuid
            self.uniqueid = str(uuid.uuid4())


@dataclass
class Tag:
    """Tag model - equivalent to Tag.swift"""
    id: str
    name: str
    color: str