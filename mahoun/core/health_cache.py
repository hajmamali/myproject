# Health Check Caching — MAHOUN Core
"""
Caching layer for health checks to improve performance.
Prevents excessive health check calls.
"""

import time
import threading
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from .health_checker import HealthChecker, ComponentHealth, HealthStatus


@dataclass
class CachedHealthResult:
    """Cached health check result"""
    result: Dict[str, Any]
    timestamp: float
    ttl: float  # Time-to-live in seconds


class HealthCheckCache:
    """
    Thread-safe cache for health check results.
    
    Features:
    - TTL-based expiration
    - Component-specific caching
    - Thread-safe operations
    """
    
    def __init__(self, default_ttl: float = 30.0):
        """
        Initialize health check cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 30s)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CachedHealthResult] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached health check result if not expired.
        
        Args:
            key: Cache key (e.g., "all", "ollama", "refactored.hybrid_search")
            
        Returns:
            Cached result or None if expired/missing
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            cached = self._cache[key]
            if time.time() - cached.timestamp > cached.ttl:
                # Expired, remove
                del self._cache[key]
                return None
            
            return cached.result
    
    def set(self, key: str, result: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """
        Cache health check result.
        
        Args:
            key: Cache key
            result: Health check result
            ttl: Time-to-live in seconds (default: self.default_ttl)
        """
        with self._lock:
            self._cache[key] = CachedHealthResult(
                result=result,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear cache entry or all cache.
        
        Args:
            key: Specific key to clear (None = clear all)
        """
        with self._lock:
            if key is None:
                self._cache.clear()
            elif key in self._cache:
                del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "cached_keys": list(self._cache.keys()),
                "cache_size": len(self._cache),
                "default_ttl": self.default_ttl
            }


class CachedHealthChecker(HealthChecker):
    """
    Health checker with caching support.
    
    Extends HealthChecker with caching to reduce load.
    """
    
    def __init__(self, cache_ttl: float = 30.0):
        """
        Initialize cached health checker.
        
        Args:
            cache_ttl: Cache TTL in seconds (default: 30s)
        """
        super().__init__()
        self.cache = HealthCheckCache(default_ttl=cache_ttl)
    
    async def check_all_cached(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Run all health checks with caching.
        
        Args:
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Health check results
        """
        if use_cache:
            cached = self.cache.get("all")
            if cached is not None:
                return cached
        
        # Run checks
        result = await self.check_all()
        
        # Cache result
        if use_cache:
            self.cache.set("all", result)
        
        return result
    
    async def check_component_cached(
        self,
        component_name: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Check specific component with caching.
        
        Args:
            component_name: Component name
            use_cache: Whether to use cache
            
        Returns:
            Component health status
        """
        if use_cache:
            cached = self.cache.get(component_name)
            if cached is not None:
                return cached
        
        # Run check based on component name
        if component_name == "ollama":
            health = await self.check_ollama()
        elif component_name == "vector_store":
            health = await self.check_vector_store()
        elif component_name == "graph":
            health = await self.check_graph()
        elif component_name == "reasoning":
            health = await self.check_reasoning()
        elif component_name.startswith("refactored."):
            refactored_health = await self.check_refactored_modules()
            health = refactored_health.get(component_name)
            if health is None:
                raise ValueError(f"Refactored module '{component_name}' not found")
        elif component_name in ["postgresql", "redis"]:
            databases_health = await self.check_databases()
            health = databases_health.get(component_name)
            if health is None:
                raise ValueError(f"Database '{component_name}' not found")
        elif component_name.startswith("agent."):
            agents_health = await self.check_agents()
            agent_name = component_name.replace("agent.", "")
            health = agents_health.get(agent_name)
            if health is None:
                raise ValueError(f"Agent '{agent_name}' not found")
        else:
            raise ValueError(f"Unknown component: '{component_name}'")
        
        result = health.to_dict()
        
        # Cache result
        if use_cache:
            self.cache.set(component_name, result)
        
        return result

