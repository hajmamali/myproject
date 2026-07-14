"""
Enhanced Health Check API Router
=================================
Comprehensive health check endpoints using HealthChecker.

Endpoints:
- GET /health/v2 - Basic health check
- GET /health/v2/detailed - Comprehensive health check
- GET /health/v2/component/{component} - Component-specific health check
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import Any, Dict, Optional
import logging

from mahoun.infrastructure.health_checker import HealthChecker
from mahoun.core.health_cache import CachedHealthChecker

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health/v2",
    tags=["health-v2"],
    responses={
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "",
    summary="Basic health check (v2)",
    description="Quick health check to verify API is running"
)
async def basic_health_check() -> Dict[str, Any]:
    """
    Basic health check
    
    Returns simple status to verify API is responsive.
    """
    return {
        "status": "healthy",
        "service": "MAHOUN Enterprise API",
        "version": "2.0.0"
    }


@router.get(
    "/detailed",
    summary="Detailed health check (v2)",
    description="""
    Comprehensive health check for all system components.
    
    Checks:
    - Ollama LLM Service
    - ChromaDB/VectorStore
    - Neo4j/Graph (if enabled)
    - UltraReasoningService
    - All registered agents
    
    Returns overall status and individual component statuses.
    """
)
async def detailed_health_check(
    use_cache: bool = Query(True, description="Use cached results if available"),
    cache_ttl: float = Query(30.0, description="Cache TTL in seconds")
) -> Dict[str, Any]:
    """
    Comprehensive health check for all components
    
    Args:
        use_cache: Whether to use cached results (default: True)
        cache_ttl: Cache TTL in seconds (default: 30s)
    
    Returns:
        Dictionary with overall status and component details
    """
    try:
        checker = CachedHealthChecker(cache_ttl=cache_ttl)
        results = await checker.check_all_cached(use_cache=use_cache)
        
        # Add cache info
        results["cache_info"] = {
            "cached": use_cache,
            "cache_stats": checker.cache.get_stats()
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get(
    "/component/{component_name}",
    summary="Component-specific health check",
    description="""
    Health check for a specific component.
    
    Available components:
    - ollama
    - vector_store
    - graph
    - reasoning
    - refactored.hybrid_search
    - refactored.gaussian_process
    - refactored.self_improvement
    - postgresql
    - redis
    - agent.{agent_name} (e.g., agent.doc_parser)
    """
)
async def component_health_check(
    component_name: str,
    use_cache: bool = Query(True, description="Use cached results if available"),
    cache_ttl: float = Query(30.0, description="Cache TTL in seconds")
) -> Dict[str, Any]:
    """
    Health check for specific component
    
    Args:
        component_name: Name of component to check
        use_cache: Whether to use cached results (default: True)
        cache_ttl: Cache TTL in seconds (default: 30s)
    
    Returns:
        Component health status
    """
    try:
        checker = CachedHealthChecker(cache_ttl=cache_ttl)
        
        # Use cached checker method
        result = await checker.check_component_cached(
            component_name,
            use_cache=use_cache
        )
        
        # Add cache info
        result["cache_info"] = {
            "cached": use_cache,
            "cache_stats": checker.cache.get_stats()
        }
        
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Component health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
