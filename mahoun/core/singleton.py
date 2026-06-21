# Thread-Safe Singleton Pattern — MAHOUN Core
"""
Thread-safe singleton implementation for service instances.
Replaces global variables with proper singleton pattern.
"""

import threading
from typing import Any, Callable, Generic, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ThreadSafeSingleton(Generic[T]):
    """
    Thread-safe singleton pattern implementation.
    
    Usage:
        class MyService:
            pass
        
        service_singleton = ThreadSafeSingleton[MyService]()
        
        # Get instance (creates if doesn't exist)
        service = service_singleton.get_instance(
            factory=lambda: MyService()
        )
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize singleton.
        
        Args:
            name: Optional name for logging
        """
        self._instance: Optional[T] = None
        self._lock = threading.RLock()
        self._name = name or "Singleton"
        self._initialized = False
    
    def get_instance(self, factory: Callable[[], T], *args, **kwargs) -> T:
        """
        Get singleton instance, creating if necessary.
        
        Args:
            factory: Factory function to create instance
            *args: Arguments for factory
            **kwargs: Keyword arguments for factory
            
        Returns:
            Singleton instance
        """
        if self._instance is None:
            with self._lock:
                # Double-check locking pattern
                if self._instance is None:
                    logger.debug(f"Creating {self._name} instance")
                    self._instance = factory(*args, **kwargs)
                    self._initialized = True
                    logger.debug(f"{self._name} instance created")
        
        return self._instance
    
    def reset(self) -> None:
        """
        Reset singleton (useful for testing).
        """
        with self._lock:
            self._instance = None
            self._initialized = False
            logger.debug(f"{self._name} instance reset")
    
    def is_initialized(self) -> bool:
        """Check if singleton is initialized."""
        return self._initialized
    
    def get_instance_unsafe(self) -> Optional[T]:
        """
        Get instance without creating (may return None).
        Use only when you're sure instance exists.
        """
        return self._instance

