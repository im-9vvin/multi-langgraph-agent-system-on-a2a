"""Logging configuration for time agent."""

import logging
import sys
from typing import Optional

from .config import settings


def setup_logging(
    level: Optional[str] = None,
    format: Optional[str] = None
):
    """Set up logging configuration.
    
    Args:
        level: Logging level (defaults to settings)
        format: Log format string
    """
    log_level = level or settings.log_level
    log_format = format or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Set our module loggers
    logging.getLogger("time_agent").setLevel(getattr(logging, log_level.upper()))


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)