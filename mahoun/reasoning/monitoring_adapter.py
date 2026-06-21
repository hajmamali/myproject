"""
Monitoring Adapter for Reasoning Module
========================================

Provides optional monitoring/observability integration without
creating compile-time architectural boundary violations.

ARCHITECTURE:
- Reasoning (core) → Monitoring (non-core): Runtime-only dependency
- Graceful degradation: No-op decorator when monitoring unavailable
- Zero performance overhead when monitoring disabled

DESIGN PATTERN:
- Decorator Pattern with Null Object fallback
- Lazy import for optional dependencies
"""

import logging
from typing import Callable, TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def get_legal_query_decorator() -> Callable[[F], F]:
    """
    Get legal query tracking decorator with runtime import.
    
    Returns a decorator that tracks legal query metrics if monitoring
    is available, otherwise returns a no-op pass-through decorator.
    
    Returns:
        Decorator function (either real or no-op)
        
    Thread Safety:
        Thread-safe - no shared mutable state
        
    Performance:
        O(1) - Simple import check
        No-op decorator has zero overhead
        
    Example:
        >>> decorator = get_legal_query_decorator()
        >>> @decorator
        ... async def generate_verdict(self, question, facts):
        ...     return verdict
    """
    try:
        from mahoun.monitoring.legal_metrics import track_legal_query_decorator
        logger.debug("Legal query monitoring decorator loaded")
        return track_legal_query_decorator
        
    except ImportError:
        logger.debug("Monitoring unavailable, using no-op decorator")
        
        # No-op decorator for graceful degradation
        def noop_decorator(func: F) -> F:
            """Pass-through decorator when monitoring unavailable."""
            return func
        
        return noop_decorator
    
    except Exception as e:
        logger.warning(f"Failed to load monitoring decorator: {e}")
        
        # Fallback no-op decorator
        def noop_decorator(func: F) -> F:
            return func
        
        return noop_decorator


# Pre-initialize decorator at module load for performance
track_legal_query_decorator = get_legal_query_decorator()


__all__ = ['track_legal_query_decorator', 'get_legal_query_decorator']
