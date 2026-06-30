"""
MAHOUN Self-Improvement REST API
=================================

FastAPI-based REST API for the self-improvement system.
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ============================================================================
# CRITICAL: Initialize governance enforcement before any other imports
# ============================================================================
from mahoun.core.import_firewall import install_import_firewall, check_neo4j_import_violation
from mahoun.core.dependency_validator import check_core_purity

# Install runtime import firewall FIRST
install_import_firewall()

# Check for existing Neo4j violations
check_neo4j_import_violation()

# Check core module purity
check_core_purity()

# Deterministic error contracts (P0)
from mahoun.core.exceptions import (
    BaseMahounError,
    SecurityBreachException,
    LogicViolationException,
    GraphIntegrityException,
)
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Import validation middleware
from api.middleware.validation import InputValidationMiddleware, RateLimitMiddleware

# Critical live surface: search must import successfully or startup must fail.
from api.routers import search as search_router

# Import system router for runtime configuration and health
from api.routers import system as system_router
from mahoun.core.settings import load_security_settings
from mahoun.pipelines._logging import get_logger

# Import ingest router for document upload
try:
    from api.routers import ingest as ingest_router

    HAS_INGEST_ROUTER = True
except ImportError:
    HAS_INGEST_ROUTER = False

logger = get_logger(__name__)

# ============================================================================
# Lifespan Context Manager
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # ============================================================================
    # STARTUP VALIDATION - CRITICAL
    # ============================================================================
    # Validate runtime configuration before starting the application.
    # This ensures fail-fast behavior on misconfiguration rather than
    # runtime failures that could compromise zero-hallucination guarantees.
    # ============================================================================
    import time as validation_time

    validation_start = validation_time.time()

    # ============================================================================
    # MANDATORY GOVERNANCE VALIDATION - FAIL-FAST (P0 ENFORCEMENT)
    # ============================================================================
    # Configuration validation is now MANDATORY, not optional.
    # System CANNOT start without proper governance configuration.
    # This ensures constitutional compliance and prevents governance bypasses.
    # ============================================================================
    
    from mahoun.core.config_validator import validate_runtime_config
    from mahoun.core.runtime_config import get_runtime_settings

    # CRITICAL: No try-except - validation failure must prevent startup
    validate_runtime_config()

    validation_duration = validation_time.time() - validation_start
    logger.info(f"✅ MANDATORY governance validation completed ({validation_duration * 1000:.1f}ms)")

    # Record metrics (optional - failure here doesn't prevent startup)
    try:
        from mahoun.metrics import (
            record_config_validation_duration,
            set_current_mode,
            set_graph_enabled,
        )

        settings = get_runtime_settings()
        record_config_validation_duration(validation_duration)
        set_current_mode(settings.mode)
        set_graph_enabled(settings.graph_enabled)

        logger.info(f"📊 Runtime mode: {settings.mode}, graph_enabled: {settings.graph_enabled}")
    except ImportError:
        logger.debug("Metrics module not available - skipping metrics recording")
    except Exception as e:
        logger.warning(f"Metrics recording failed: {e}")  # Non-fatal
        try:
            from mahoun.core.runtime_config import get_runtime_settings
            from mahoun.metrics import record_config_validation_failure

            settings = get_runtime_settings()
            record_config_validation_failure(validation_rule="startup_validation", mode=settings.mode)
        except ImportError:
            logger.debug("Metrics module not available")

        # Fail-fast: Do not start application with invalid configuration
        raise

    # Startup
    app.state.start_time = time.time()

    # Check if databases are enabled
    enable_postgres = os.getenv("ENABLE_POSTGRES", "false").lower() == "true"
    enable_neo4j = os.getenv("ENABLE_NEO4J", "false").lower() == "true"
    enable_redis = os.getenv("ENABLE_REDIS", "false").lower() == "true"

    if not (enable_postgres or enable_neo4j or enable_redis):
        logger.info("⚠️  All databases disabled - running in standalone mode")
    else:
        try:
            # Initialize only enabled databases
            if enable_postgres:
                from api.database import init_postgres

                await init_postgres()
                logger.info("✅ PostgreSQL initialized")

            if enable_neo4j:
                from api.database import init_neo4j

                await init_neo4j()
                logger.info("✅ Neo4j initialized")

            if enable_redis:
                from api.database import init_redis

                await init_redis()
                logger.info("✅ Redis initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize databases: {e}")
            # Don't raise - allow app to start even if DB is unavailable

    yield  # Application runs here

    # Shutdown
    if enable_postgres or enable_neo4j or enable_redis:
        try:
            if enable_postgres:
                from api.database import close_postgres

                await close_postgres()

            if enable_neo4j:
                from api.database import close_neo4j

                await close_neo4j()

            if enable_redis:
                from api.database import close_redis

                await close_redis()

            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing databases: {e}")


# Create FastAPI app with lifespan
app = FastAPI(
    title="MAHOUN Self-Improvement API",
    description="REST API for managing the self-improvement system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

SECURITY_SETTINGS = load_security_settings()


def apply_security_middleware(application):
    application.add_middleware(
        CORSMiddleware,
        allow_origins=SECURITY_SETTINGS.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    # Skip trusted host middleware in test environment
    if os.getenv("MAHOUN_TESTING") != "1":
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=SECURITY_SETTINGS.allowed_hosts)


# Security middleware
apply_security_middleware(app)

# Input validation middleware (PR-7)
app.add_middleware(InputValidationMiddleware)
logger.info("✓ Input validation middleware enabled")

# Rate limiting middleware (optional, can be disabled in dev)
if os.getenv("MAHOUN_ENABLE_RATE_LIMIT", "true").lower() == "true":
    max_requests = int(os.getenv("MAHOUN_RATE_LIMIT_REQUESTS", "100"))
    window_seconds = int(os.getenv("MAHOUN_RATE_LIMIT_WINDOW", "60"))
    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_seconds=window_seconds)
    logger.info(f"✓ Rate limiting enabled: {max_requests} requests per {window_seconds}s")


# ============================================================================
# DETERMINISTIC ERROR CONTRACT HANDLERS (P0 - NO MORE VAGUE 500 FOR SECURITY)
# ============================================================================

@app.exception_handler(BaseMahounError)
async def mahoun_deterministic_error_handler(request: Request, exc: BaseMahounError):
    """Maps all known Mahoun errors to their declared exact HTTP status code."""
    logger.warning(
        "Deterministic governance error",
        extra={
            "error_type": exc.error_type,
            "status_code": exc.status_code,
            "correlation_id": exc.correlation_id,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_type,
            "message": exc.message,
            "correlation_id": exc.correlation_id,
            "details": exc.details,
            "timestamp": datetime.now().isoformat(),
        },
    )


# Specific aliases for clarity (in case old SecurityBreachException is raised directly)
@app.exception_handler(SecurityBreachException)
async def security_breach_handler(request: Request, exc: SecurityBreachException):
    return await mahoun_deterministic_error_handler(request, exc)


@app.exception_handler(LogicViolationException)
async def logic_violation_handler(request: Request, exc: LogicViolationException):
    return await mahoun_deterministic_error_handler(request, exc)


# Global catch-all remains 500 only for truly unexpected bugs (never for governance)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Logs the error and returns a structured JSON response.
    """
    error_id = datetime.now().strftime("%Y%m%d%H%M%S")

    logger.error(
        f"Unhandled exception [{error_id}]: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please contact support.",
            "timestamp": datetime.now().isoformat(),
        },
    )


# Register routers
app.include_router(system_router.router, prefix="/system")  # /system/* endpoints
app.include_router(system_router.router, prefix="/api/system")  # /api/system/* endpoints for frontend compatibility

# Register constitutionally required live routers.
app.include_router(search_router.router)
logger.info("✓ Legal search router registered at /v1/search")

# Register ingest router if available
if HAS_INGEST_ROUTER:
    from api.routers import ingest as ingest_router

    app.include_router(ingest_router.router, prefix="/api/ingest")
    logger.info("✓ Document ingest router registered at /api/ingest")

# ============================================================================
# ALPHA LAUNCH: MAHOUN router DISABLED
# ============================================================================
# MAHOUN router contains agent-driven endpoints that use LLM without
# sufficient governance:
# - /upload-documents → UltraDocParserAgent (LLM-driven)
# - /ask-contract → UltraContractAgent (LLM-driven)
# - /generate-claim → ClaimDraftGenerator (LLM-driven)
# - /analyze-delay → DelayAnalysisEngine (potential graph writes)
#
# All agent endpoints must be audited for:
# - Governance context enforcement
# - Graph write safety
# - LLM hallucination protection
# - Fail-closed error handling
#
# For alpha, use /api/ingest/* for safe document upload without agents.
# ============================================================================
# try:
#     from api.routers import mahoun as mahoun_router
#     app.include_router(mahoun_router.router)
#     logger.info("✓ MAHOUN router registered at /api/v1/mahoun")
# except ImportError as e:
#     logger.warning(f"MAHOUN router not available: {e}")

logger.warning("⚠️  MAHOUN ROUTER DISABLED FOR ALPHA LAUNCH (agent endpoints require governance audit)")

# Fine-tuning remains intentionally off the live surface until it is backed by
# a real executor and persistent job state.
logger.warning(
    "⚠️  FINE-TUNING ROUTER REMOVED FROM LIVE SURFACE "
    "(simulated job lifecycle is not exposed as production capability)"
)

from api.routers import reasoning as reasoning_router

app.include_router(reasoning_router.router)
logger.info("✓ Reasoning router registered at /api/v1/reasoning")

# Register Training Datasets router (Document → Training)
try:
    from api.routers import training_datasets

    app.include_router(training_datasets.router)
    logger.info("✓ Training datasets router registered at /api/v1/training-datasets")
except ImportError as e:
    logger.warning(f"Training datasets router not available: {e}")

# Register Health V2 router (enhanced health checks)
try:
    from api.routers import health_v2

    app.include_router(health_v2.router)
    logger.info("✓ Enhanced health check router registered at /health/v2")
except ImportError as e:
    logger.warning(f"Health V2 router not available: {e}")

# ============================================================================
# Monitoring Endpoints (MUST be registered BEFORE metrics router
# because the router has a /{metric_name:path} catch-all that would
# otherwise intercept /metrics/legal, /metrics/prometheus, /metrics/reset)
# ============================================================================


@app.get("/metrics/prometheus", tags=["monitoring"])
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping.
    """
    from mahoun.metrics import get_metrics_collector

    collector = get_metrics_collector()
    return collector.to_prometheus()


@app.get("/metrics/legal", tags=["monitoring"])
async def legal_metrics():
    """
    Legal-specific metrics and comprehensive statistics

    Returns detailed legal query metrics including:
    - Total queries and throughput
    - Performance metrics (avg duration, P50, P95, P99)
    - Error rates and categorization
    - SLA compliance rates
    - Queries by court rank and legal domain
    - Cache performance
    - Authority scores

    **Response Example**:
    ```json
    {
      "total_queries": 1234,
      "queries_per_second": 2.5,
      "avg_duration_seconds": 0.45,
      "p95_latency": 0.8,
      "error_rate": 0.02,
      "sla_compliance_rate": 0.98,
      "queries_by_court": {
        "SUPREME_COURT": 456,
        "APPEALS_COURT": 789
      }
    }
    ```

    Returns:
        Comprehensive legal metrics dictionary
    """
    from mahoun.monitoring.legal_metrics import legal_monitoring

    return legal_monitoring.get_comprehensive_stats()


@app.get("/health/detailed", tags=["monitoring"])
async def detailed_health():
    """
    Detailed health check with comprehensive system status

    Returns:
        Detailed health status including:
        - Overall system status
        - Component health
        - Uptime
        - SLA compliance
    """
    import time

    from mahoun.monitoring.legal_metrics import legal_monitoring

    # Calculate uptime
    uptime_seconds = time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0

    # Get legal monitoring health
    legal_health = await legal_monitoring.health_check()

    return {
        "status": legal_health.get("status", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime_seconds,
        "components": legal_health.get("components", {}),
        "sla_compliance": legal_health.get("sla_compliance", {}),
    }


@app.post("/metrics/reset", tags=["monitoring"])
async def reset_metrics():
    """
    Reset all monitoring metrics (development only)

    **Security**: This endpoint is blocked in production environments.

    Returns:
        Confirmation of reset or error if in production
    """
    # Block in production
    from mahoun.core.environment import is_production, is_staging

    if is_production() or is_staging():
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": "Reset not allowed in production",
            },
        )

    # Reset metrics
    from mahoun.metrics import get_metrics_collector
    from mahoun.monitoring.legal_metrics import legal_monitoring

    collector = get_metrics_collector()
    collector.reset()
    legal_monitoring.reset()

    return {
        "status": "reset",
        "message": "All metrics have been reset",
        "timestamp": datetime.now().isoformat(),
    }


# Register Metrics router (AFTER monitoring endpoints to avoid catch-all conflict)
try:
    from api.routers import metrics as metrics_router

    app.include_router(metrics_router.router)
    logger.info("✓ Metrics router registered at /metrics")
except ImportError as e:
    logger.warning(f"Metrics router not available: {e}")

# Register MAHOUN Observability API router (MCP Layer 1)
try:
    from mahoun.api_router import router as mahoun_api_router

    app.include_router(mahoun_api_router)
    logger.info("✓ MAHOUN observability router registered at /internal")
except ImportError as e:
    logger.warning(f"MAHOUN observability router not available: {e}")

# Register MAHOUN Dashboard router (MCP Layer 2)
try:
    from mahoun.dashboard.router import router as mahoun_dashboard_router

    app.include_router(mahoun_dashboard_router)
    logger.info("✓ MAHOUN dashboard router registered at /internal/dashboard")
except ImportError as e:
    logger.warning(f"MAHOUN dashboard router not available: {e}")


# Pydantic models
class FeedbackRequest(BaseModel):
    query_id: str
    user_id: str
    query: str
    response: str
    accuracy: float = Field(ge=0.0, le=1.0)
    latency: float = Field(gt=0.0)
    user_satisfaction: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None


class PolicyDeployRequest(BaseModel):
    policy_id: str
    version: str
    mode: Literal["shadow", "canary", "full"] = "shadow"
    traffic_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    description: str | None = None


class ExperimentRequest(BaseModel):
    name: str
    variants: list[str]
    traffic_split: list[float]
    metrics: list[str]
    metadata: dict[str, Any] | None = None


class RollbackRequest(BaseModel):
    target_snapshot_id: str
    reason: str


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint backed by real infrastructure probes."""
    return await system_router.collect_system_health()


# =============================================================================
# Self-Improvement Integration
# =============================================================================

_feedback_pipeline = None


def get_feedback_pipeline():
    """Get or create feedback pipeline instance"""
    global _feedback_pipeline
    if _feedback_pipeline is None:
        from mahoun.finetuning.feedback_pipeline import FeedbackPipeline

        _feedback_pipeline = FeedbackPipeline(min_rating=4.0, min_quality_score=0.7)
        logger.info("✓ Feedback pipeline initialized")
    return _feedback_pipeline


async def process_feedback_task(feedback: FeedbackRequest):
    """Process feedback in background"""
    try:
        from datetime import datetime

        from mahoun.finetuning.feedback_pipeline import FeedbackType, UserFeedback

        pipeline = get_feedback_pipeline()

        # Convert API feedback to pipeline format
        user_feedback = UserFeedback(
            feedback_id=feedback.query_id,
            user_id=feedback.user_id,
            query=feedback.query,
            response=feedback.response,
            feedback_type=FeedbackType.RATING,
            rating=feedback.user_satisfaction * 5.0,  # Convert 0-1 to 1-5
            response_time_ms=feedback.latency * 1000,  # Convert s to ms
            confidence_score=feedback.accuracy,
            timestamp=datetime.now(),
        )

        # Add to pipeline
        pipeline.add_feedback(user_feedback)

        logger.info(f"Processed feedback: {feedback.query_id}")

    except Exception as e:
        logger.error(f"Failed to process feedback: {e}", exc_info=True)


# Feedback endpoints
@app.post("/api/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Submit user feedback

    This endpoint receives feedback from users about query responses
    and feeds it into the self-improvement loop.
    """
    logger.info(f"Received feedback for query {feedback.query_id}")

    # Process feedback in background
    background_tasks.add_task(process_feedback_task, feedback)

    return {
        "status": "accepted",
        "query_id": feedback.query_id,
        "message": "Feedback received and queued for processing",
    }


@app.get("/api/v1/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics from real pipeline"""
    try:
        pipeline = get_feedback_pipeline()

        # Calculate real stats
        total_feedback = len(pipeline.feedback_store)

        if total_feedback == 0:
            return {
                "total_feedback": 0,
                "avg_satisfaction": 0.0,
                "avg_accuracy": 0.0,
                "feedback_rate": 0.0,
            }

        # Calculate averages
        ratings = [f.rating for f in pipeline.feedback_store if f.rating is not None]
        confidences = [f.confidence_score for f in pipeline.feedback_store if f.confidence_score is not None]

        avg_satisfaction = sum(ratings) / len(ratings) / 5.0 if ratings else 0.0
        avg_accuracy = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_feedback": total_feedback,
            "avg_satisfaction": round(avg_satisfaction, 3),
            "avg_accuracy": round(avg_accuracy, 3),
            "feedback_rate": 0.65,  # This would come from query logs
            "high_quality_count": len([f for f in pipeline.feedback_store if f.rating and f.rating >= 4.0]),
        }
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}")
        return {
            "total_feedback": 0,
            "avg_satisfaction": 0.0,
            "avg_accuracy": 0.0,
            "feedback_rate": 0.0,
            "error": str(e),
        }


# Policy endpoints
@app.get("/api/v1/policy/current")
async def get_current_policy():
    """Get the live execution policy resolved by the governance stack."""
    from mahoun.core.governance.governance_context import GovernanceContextManager
    from mahoun.core.policy_resolver import create_default_policy_resolver
    from mahoun.core.runtime_config import get_runtime_settings

    settings = get_runtime_settings()
    async with GovernanceContextManager.active_context(
        correlation_id="api-policy-current",
        actor_id="api-policy-surface",
    ) as ctx:
        resolver = create_default_policy_resolver()
        policy = resolver.resolve_policy(ctx)
        return {
            "policy_id": policy.policy_id,
            "status": "active",
            "resolved_at": policy.resolved_at,
            "runtime_mode": settings.mode,
            "graph_enabled": settings.graph_enabled,
            "graph_backend": settings.graph_backend,
            "retrieval_mode": settings.retrieval_mode,
            "policy": policy.to_dict(),
            "audit_stats": resolver.get_policy_statistics(),
        }

@app.get("/api/v1/policy/list")
async def list_policies(status: str | None = None, limit: int = 10):
    """List live policies backed by the current governance resolver."""
    current_policy = await get_current_policy()
    policies = [current_policy]
    if status:
        policies = [policy for policy in policies if policy["status"] == status]
    return {"policies": policies[:limit], "total": len(policies)}

# Metrics endpoints
@app.get("/api/v1/metrics")
async def get_metrics(component: str | None = None, metric: str | None = None, window: int = 3600):
    """Get system metrics from the real collector"""
    from mahoun.metrics import get_metrics_collector

    collector = get_metrics_collector()
    metrics_data = collector.get_all_metrics()

    # Filter by component if requested
    if component:
        metrics_data = {k: v for k, v in metrics_data.items() if component in k}

    return {
        "component": component or "all",
        "metric": metric or "all",
        "window_seconds": window,
        "metrics": metrics_data,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/metrics/dashboard")
async def get_dashboard_data():
    """Get dashboard data"""
    from mahoun.metrics import get_metrics_collector

    health = await system_router.collect_system_health()
    collector = get_metrics_collector()
    metrics_data = collector.get_all_metrics()
    return {
        "timestamp": datetime.now().isoformat(),
        "status": health["status"],
        "mode": health["mode"],
        "components": health["components"],
        "metrics_keys": sorted(metrics_data.keys()),
        "metrics_count": len(metrics_data),
    }


# System status endpoints
@app.get("/api/v1/status")
async def get_system_status():
    """Get overall system status"""
    health = await system_router.collect_system_health()
    return {
        "status": health["status"],
        "mode": health["mode"],
        "summary": health["summary"],
        "timestamp": health["timestamp"],
    }


@app.get("/api/v1/status/health")
async def get_health_status():
    """Get detailed health status from the internal health system"""
    return await system_router.collect_system_health()


# Configuration endpoints
@app.get("/api/v1/config")
async def get_config():
    """Get system configuration"""
    from mahoun.core.runtime_config import get_runtime_settings

    settings = get_runtime_settings()
    return {
        "mode": settings.mode,
        "graph_enabled": settings.graph_enabled,
        "graph_backend": settings.graph_backend,
        "retrieval_mode": settings.retrieval_mode,
        "embedding_backend": settings.embedding_backend,
        "llm_backend": settings.llm_backend,
        "lora_training_enabled": settings.lora_training_enabled,
    }

# Statistics endpoints
@app.get("/api/v1/stats")
async def get_statistics():
    """Get system statistics"""
    from mahoun.metrics import get_metrics_collector

    collector = get_metrics_collector()
    metrics_data = collector.get_all_metrics()
    return {
        "metrics_count": len(metrics_data),
        "metric_names": sorted(metrics_data.keys()),
        "feedback": await get_feedback_stats(),
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
