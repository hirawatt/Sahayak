"""
Logging configuration for Horizon AI Assistant Backend
"""

import logging
import sys
from pathlib import Path
import structlog
from rich.logging import RichHandler
from rich.console import Console


def setup_logging():
    """Setup structured logging with Rich formatting"""
    
    # Create logs directory
    log_dir = Path.home() / ".horizon-ai" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup standard logging
    console = Console()
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                console=console,
                show_path=True
            )
        ]
    )
    
    # File handler for persistent logging
    file_handler = logging.FileHandler(
        log_dir / "horizon-ai.log",
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add file handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("evdev").setLevel(logging.WARNING)
    logging.getLogger("dbus").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    return structlog.get_logger("horizon-ai")