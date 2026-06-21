"""
Core Logging Utility
====================
Centralized logging configuration for Mahoun platform.

این ماژول یک wrapper ساده روی logging استاندارد Python است.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: Optional[int] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup and return a configured logger.
    
    Args:
        name: Logger name (usually module name)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    if level is None:
        level = logging.INFO
    logger.setLevel(level)
    
    # Only add handler if logger doesn't have one
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Set format
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
