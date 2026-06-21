# Standardized Error Handling — MAHOUN Core
"""
Standardized error handling utilities for consistent error management.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Type
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    module: str
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ErrorHandler:
    """
    Standardized error handler with logging and context.
    """
    
    @staticmethod
    def handle_error(
        error: Exception,
        operation: str,
        module: str,
        metadata: Optional[Dict[str, Any]] = None,
        log_level: int = logging.ERROR,
        reraise: bool = False
    ) -> ErrorContext:
        """
        Handle an error with standardized logging and context.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            module: Module where error occurred
            metadata: Additional context metadata
            log_level: Logging level (default: ERROR)
            reraise: Whether to re-raise the exception
            
        Returns:
            ErrorContext with error information
        """
        error_context = ErrorContext(
            operation=operation,
            module=module,
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=traceback.format_exc(),
            metadata=metadata or {}
        )
        
        # Log error with context
        log_message = (
            f"Error in {module}.{operation}: {error_context.error_type}: "
            f"{error_context.error_message}"
        )
        
        if metadata:
            log_message += f" | Metadata: {metadata}"
        
        logger.log(log_level, log_message, exc_info=True)
        
        if reraise:
            raise error
        
        return error_context
    
    @staticmethod
    def handle_specific_error(
        error: Exception,
        operation: str,
        module: str,
        expected_errors: Dict[Type[Exception], str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """
        Handle specific error types with custom messages.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation
            module: Module where error occurred
            expected_errors: Dict mapping exception types to custom messages
            metadata: Additional context
            
        Returns:
            ErrorContext if error was handled, None if not in expected_errors
        """
        error_type = type(error)
        
        if error_type in expected_errors:
            custom_message = expected_errors[error_type]
            logger.warning(
                f"{module}.{operation}: {custom_message} ({error_type.__name__})"
            )
            
            return ErrorContext(
                operation=operation,
                module=module,
                error_type=error_type.__name__,
                error_message=custom_message,
                metadata=metadata or {}
            )
        
        # Not an expected error, use standard handling
        return ErrorHandler.handle_error(
            error, operation, module, metadata, reraise=True
        )


# Convenience function
def handle_error(
    error: Exception,
    operation: str,
    module: str,
    metadata: Optional[Dict[str, Any]] = None,
    log_level: int = logging.ERROR,
    reraise: bool = False
) -> ErrorContext:
    """
    Convenience function for error handling.
    
    Usage:
        try:
            result = risky_operation()
        except Exception as e:
            context = handle_error(e, "risky_operation", __name__)
            return fallback_result
    """
    return ErrorHandler.handle_error(
        error, operation, module, metadata, log_level, reraise
    )

