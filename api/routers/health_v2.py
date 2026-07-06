"""
Enhanced Health Check API Router
=================================
Comprehensive health check endpoints using HealthChecker.

Endpoints:
- GET /health/v2 - Basic health check
- GET /health/v2/detailed - Comprehensive health check
- GET /health/v2/component/{component} - Component-specific health check
- GET /health/v2/ai-runtime - AI Runtime health check (GGUF models, embeddings, governance)
- GET /health/v2/ai-runtime/readiness - Kubernetes-style readiness probe
- GET /health/v2/ai-runtime/liveness - Kubernetes-style liveness probe
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import Any, Dict, Optional
import logging
from pathlib import Path
import os

from api.routers.system import collect_system_health
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

# AI Runtime health checker (lazy-initialized)
_ai_health_checker = None


def get_ai_health_checker():
    """Get or create AI runtime health checker instance"""
    global _ai_health_checker
    if _ai_health_checker is None:
        from mahoun.ai.health import AIRuntimeHealthChecker
        
        # Get models directory from environment or use default
        models_dir = os.getenv("MAHOUN_MODELS_DIR", "/models")
        data_dir = os.getenv("MAHOUN_DATA_DIR", "/data")
        
        _ai_health_checker = AIRuntimeHealthChecker(
            models_dir=models_dir,
            data_dir=data_dir,
            enable_detailed_metrics=True
        )
        logger.info(f"AIRuntimeHealthChecker initialized: models={models_dir}, data={data_dir}")
    
    return _ai_health_checker


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
    return await collect_system_health()


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


# ============================================================================
# AI RUNTIME HEALTH ENDPOINTS (Phase D.3.2)
# ============================================================================


@router.get(
    "/ai-runtime",
    summary="AI Runtime comprehensive health check",
    description="""
    Comprehensive health check for AI runtime components.
    
    Monitors:
    - **Model Runtime**: GGUF model availability and accessibility
    - **Embedding Service**: Local embedding models (sentence-transformers)
    - **Memory Manager**: System resource utilization (CPU, RAM, disk)
    - **Governance Validator**: FortressValidator integration status
    - **Network Isolation**: Air-gap compliance verification
    
    Returns detailed status, metrics, and latency for each component.
    Useful for production monitoring and debugging.
    """
)
async def ai_runtime_health_check(
    include_details: bool = Query(
        False, 
        description="Include detailed metrics and component information"
    )
) -> Dict[str, Any]:
    """
    Comprehensive AI runtime health check
    
    Args:
        include_details: Include detailed component metrics and diagnostics
    
    Returns:
        Complete health status with system metrics and component checks
        
    Response Structure:
        - status: overall health (healthy/degraded/unhealthy/unknown)
        - timestamp: ISO 8601 timestamp
        - uptime_seconds: runtime uptime
        - version: runtime version
        - checks: individual component checks with status and latency
        - system: resource utilization metrics
        - latency_ms: total health check latency
        - details: (optional) detailed component information
    """
    try:
        checker = get_ai_health_checker()
        health_data = await checker.check_health(include_details=include_details)
        
        return health_data
        
    except Exception as e:
        logger.error(f"AI runtime health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "ai_runtime_health_check_failed",
                "message": str(e),
                "component": "ai_runtime"
            }
        )


@router.get(
    "/ai-runtime/readiness",
    summary="Kubernetes readiness probe",
    description="""
    Kubernetes-style readiness probe for AI runtime.
    
    Returns `ready: true` only if critical components are operational:
    - Model runtime is healthy (not unhealthy)
    - Memory resources are available (not unhealthy)
    
    Use this endpoint for Kubernetes readiness checks to ensure
    traffic is only routed to ready pods.
    
    **Kubernetes Configuration Example**:
    ```yaml
    readinessProbe:
      httpGet:
        path: /health/v2/ai-runtime/readiness
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 2
      failureThreshold: 3
    ```
    """
)
async def ai_runtime_readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe
    
    Returns:
        - ready: boolean indicating if service is ready for traffic
        - timestamp: check timestamp
        - components: status of critical components
        
    Status Codes:
        - 200: Service is ready
        - 503: Service is not ready (unavailable)
    """
    try:
        checker = get_ai_health_checker()
        readiness_data = await checker.readiness_check()
        
        # Return 503 if not ready
        if not readiness_data.get("ready", False):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=readiness_data
            )
        
        return readiness_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI runtime readiness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ready": False,
                "error": str(e),
                "timestamp": None
            }
        )


@router.get(
    "/ai-runtime/liveness",
    summary="Kubernetes liveness probe",
    description="""
    Kubernetes-style liveness probe for AI runtime.
    
    Simple health check that verifies the service can respond.
    Returns `alive: true` if the process is running and responsive.
    
    Use this endpoint for Kubernetes liveness checks to detect
    when pods need to be restarted.
    
    **Kubernetes Configuration Example**:
    ```yaml
    livenessProbe:
      httpGet:
        path: /health/v2/ai-runtime/liveness
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    ```
    """
)
async def ai_runtime_liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe
    
    Returns:
        - alive: boolean indicating if service is alive
        - timestamp: check timestamp
        - uptime_seconds: service uptime
        
    Status Codes:
        - 200: Service is alive
        - 503: Service is dead (should be restarted)
    """
    try:
        checker = get_ai_health_checker()
        liveness_data = await checker.liveness_check()
        
        return liveness_data
        
    except Exception as e:
        logger.error(f"AI runtime liveness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "alive": False,
                "error": str(e),
                "timestamp": None
            }
        )
