"""
System Health and Status Router
================================
Production-grade health checks with REAL connectivity tests

NO FAKE "ok" RESPONSES - All checks perform actual database queries
"""

import logging
from typing import Any, Dict
from datetime import datetime
import time
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, status as http_status

logger = logging.getLogger(__name__)

router = APIRouter()


async def collect_system_health() -> Dict[str, Any]:
    """Collect real system health from live backends and governed components."""
    from mahoun.core.runtime_config import get_runtime_settings
    from mahoun.core.governance.governance_context import GovernanceContextManager
    from mahoun.core.governance_kernel.kernel import KernelMutationBoundary
    from mahoun.core.policy_resolver import create_default_policy_resolver
    from mahoun.ledger.blockchain import ImmutableLedger
    from services.search.legal_search_service import LegalSearchService

    settings = get_runtime_settings()
    start_time = time.time()
    components: Dict[str, Any] = {}

    postgres_status = "unknown"
    postgres_latency = 0.0
    postgres_error = None
    if settings.enable_postgres:
        postgres_start = time.time()
        try:
            from api.database import postgres_pool

            if postgres_pool:
                async with postgres_pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    if result == 1:
                        postgres_status = "healthy"
                    else:
                        postgres_status = "unhealthy"
                        postgres_error = f"Unexpected result: {result}"
            else:
                postgres_status = "unhealthy"
                postgres_error = "Connection pool not initialized"
        except Exception as e:
            postgres_status = "unhealthy"
            postgres_error = str(e)
            logger.error("PostgreSQL health check failed: %s", e)
        postgres_latency = (time.time() - postgres_start) * 1000
    else:
        postgres_status = "disabled"
        postgres_error = "Not enabled in current runtime mode"

    components["postgresql"] = {
        "status": postgres_status,
        "latency_ms": round(postgres_latency, 2),
        "error": postgres_error,
        "checked_at": datetime.now().isoformat(),
    }

    neo4j_status = "unknown"
    neo4j_latency = 0.0
    neo4j_error = None
    if settings.graph_enabled and settings.graph_backend != "disabled_fallback":
        neo4j_start = time.time()
        try:
            from mahoun.graph.neo4j.connection import get_connection

            connection = get_connection()
            result = connection.execute_query("RETURN 1 AS test")
            if result and result[0].get("test") == 1:
                neo4j_status = "healthy"
            else:
                neo4j_status = "unhealthy"
                neo4j_error = "Query returned unexpected result"
        except Exception as e:
            neo4j_status = "unhealthy"
            neo4j_error = str(e)
            logger.error("Neo4j health check failed: %s", e)
        neo4j_latency = (time.time() - neo4j_start) * 1000
    else:
        neo4j_status = "disabled"
        neo4j_error = "Graph backend disabled in current runtime mode"

    components["neo4j"] = {
        "status": neo4j_status,
        "latency_ms": round(neo4j_latency, 2),
        "error": neo4j_error,
        "checked_at": datetime.now().isoformat(),
    }

    redis_status = "unknown"
    redis_latency = 0.0
    redis_error = None
    if settings.enable_redis:
        redis_start = time.time()
        try:
            from api.database import get_redis

            redis_client = await get_redis()
            if redis_client and await redis_client.ping():
                redis_status = "healthy"
            else:
                redis_status = "unhealthy"
                redis_error = "Redis ping failed"
        except Exception as e:
            redis_status = "unhealthy"
            redis_error = str(e)
            logger.error("Redis health check failed: %s", e)
        redis_latency = (time.time() - redis_start) * 1000
    else:
        redis_status = "disabled"
        redis_error = "Not enabled in current runtime mode"

    components["redis"] = {
        "status": redis_status,
        "latency_ms": round(redis_latency, 2),
        "error": redis_error,
        "checked_at": datetime.now().isoformat(),
    }

    governance_status = "unknown"
    governance_latency = 0.0
    governance_error = None
    governance_details: Dict[str, Any] = {}
    governance_start = time.time()
    try:
        async with GovernanceContextManager.active_context(
            correlation_id="health-governance",
            actor_id="system-healthcheck",
        ) as ctx:
            query_type = KernelMutationBoundary.classify_query("MATCH (n) RETURN n LIMIT 1")
            policy = create_default_policy_resolver().resolve_policy(ctx)
            governance_status = "healthy"
            governance_details = {
                "query_type": getattr(query_type, "value", str(query_type)),
                "policy_id": policy.policy_id,
                "view_mode": policy.view_mode.value,
                "allow_tombstones": policy.allow_tombstones,
            }
    except Exception as e:
        governance_status = "unhealthy"
        governance_error = str(e)
        logger.error("Governance kernel health check failed: %s", e)
    governance_latency = (time.time() - governance_start) * 1000

    components["governance_kernel"] = {
        "status": governance_status,
        "latency_ms": round(governance_latency, 2),
        "error": governance_error,
        "details": governance_details,
        "checked_at": datetime.now().isoformat(),
    }

    ledger_status = "unknown"
    ledger_latency = 0.0
    ledger_error = None
    ledger_details: Dict[str, Any] = {}
    ledger_start = time.time()
    try:
        ledger_path = os.getenv("MAHOUN_LEDGER_PATH", "./data/ledger.json")
        ledger = ImmutableLedger(storage_path=ledger_path)
        ledger_dir = Path(ledger_path).parent
        ledger_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=ledger_dir, prefix=".ledger_probe_", delete=True) as probe:
            probe.write(b"probe")
            probe.flush()
        ledger_status = "healthy" if ledger.verify_integrity() else "unhealthy"
        if ledger_status != "healthy":
            ledger_error = "Ledger integrity verification failed"
        ledger_details = {
            "storage_path": ledger_path,
            "chain_length": len(ledger.chain),
            "integrity": ledger.verify_integrity(),
        }
    except Exception as e:
        ledger_status = "unhealthy"
        ledger_error = str(e)
        logger.error("Ledger health check failed: %s", e)
    ledger_latency = (time.time() - ledger_start) * 1000

    components["ledger"] = {
        "status": ledger_status,
        "latency_ms": round(ledger_latency, 2),
        "error": ledger_error,
        "details": ledger_details,
        "checked_at": datetime.now().isoformat(),
    }

    retrieval_status = "unknown"
    retrieval_latency = 0.0
    retrieval_error = None
    retrieval_details: Dict[str, Any] = {}
    retrieval_start = time.time()
    try:
        service = LegalSearchService()
        await service._ensure_initialized()
        vector_manager = await service._get_vector_manager()
        graph_ops = await service._get_graph_ops()
        graph_required = settings.graph_enabled and settings.retrieval_mode == "hybrid_graph"
        retrieval_ready = vector_manager is not None and (not graph_required or graph_ops is not None)
        retrieval_status = "healthy" if retrieval_ready else "degraded"
        retrieval_details = {
            "vector_store_ready": vector_manager is not None,
            "graph_required": graph_required,
            "graph_ready": graph_ops is not None,
            "stats": service.get_stats(),
        }
        if not retrieval_ready:
            retrieval_error = "Retrieval dependencies are not fully ready"
    except Exception as e:
        retrieval_status = "unhealthy"
        retrieval_error = str(e)
        logger.error("Retrieval health check failed: %s", e)
    retrieval_latency = (time.time() - retrieval_start) * 1000

    components["retrieval"] = {
        "status": retrieval_status,
        "latency_ms": round(retrieval_latency, 2),
        "error": retrieval_error,
        "details": retrieval_details,
        "checked_at": datetime.now().isoformat(),
    }

    unhealthy_count = sum(1 for c in components.values() if c["status"] == "unhealthy")
    degraded_count = sum(1 for c in components.values() if c["status"] == "degraded")
    healthy_count = sum(1 for c in components.values() if c["status"] == "healthy")
    disabled_count = sum(1 for c in components.values() if c["status"] == "disabled")

    if unhealthy_count:
        overall_status = "unhealthy" if healthy_count == 0 else "degraded"
    elif degraded_count:
        overall_status = "degraded"
    elif healthy_count:
        overall_status = "healthy"
    else:
        overall_status = "unknown"

    return {
        "status": overall_status,
        "mode": settings.mode,
        "timestamp": datetime.now().isoformat(),
        "total_check_time_ms": round((time.time() - start_time) * 1000, 2),
        "components": components,
        "summary": {
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "disabled": disabled_count,
            "total": len(components),
        },
    }


# ============================================================================
# Real Health Check Implementation
# ============================================================================

@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """
    PRODUCTION-GRADE health check with REAL connectivity tests
    
    This endpoint performs ACTUAL checks:
    - PostgreSQL: Executes SELECT 1 query
    - Neo4j: Executes RETURN 1 query  
    - Redis: Executes PING command
    
    Returns:
    - status: "healthy" | "degraded" | "unhealthy"
    - components: Individual component health with latency
    - timestamp: ISO format timestamp
    
    All checks are REAL - no placeholders or fake responses!
    """
    return await collect_system_health()


@router.get("/status")
def get_system_status() -> Dict[str, Any]:
    """
    Lightweight system status (no heavy checks)

    Use /health for comprehensive checks
    Use /status for quick API availability
    """
    from mahoun.core.runtime_config import get_runtime_settings
    settings = get_runtime_settings()

    return {
        "status": "online",
        "mode": settings.mode,
        "timestamp": datetime.now().isoformat(),
        "message": "API is operational. Use /health for detailed checks."
    }


@router.get("/mode")
async def get_system_mode() -> Dict[str, Any]:
    """
    Get system mode information
    """
    from mahoun.core.runtime_config import get_runtime_settings
    settings = get_runtime_settings()

    return {
        "mode": settings.mode,
        "graph_enabled": settings.graph_enabled,
        "graph_backend": settings.graph_backend,
        "retrieval_mode": settings.retrieval_mode,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/info")
async def get_system_info() -> Dict[str, Any]:
    """
    Get detailed system information
    """
    from mahoun.core.runtime_config import get_runtime_settings
    settings = get_runtime_settings()

    return {
        "app_name": getattr(settings, 'app_name', 'MAHOUN'),
        "version": getattr(settings, 'version', 'unknown'),
        "environment": settings.mode,
        "features": {
            "enabled": [
                feature for feature, enabled in {
                    "search": True,
                    "ingest": True,
                    "reasoning": settings.graph_enabled,
                    "graph": settings.graph_enabled,
                    "postgres": settings.enable_postgres,
                    "redis": settings.enable_redis,
                }.items() if enabled
            ],
            "disabled": [
                feature for feature, enabled in {
                    "reasoning": settings.graph_enabled,
                    "graph": settings.graph_enabled,
                    "postgres": settings.enable_postgres,
                    "redis": settings.enable_redis,
                }.items() if not enabled
            ]
        },
        "timestamp": datetime.now().isoformat()
    }
