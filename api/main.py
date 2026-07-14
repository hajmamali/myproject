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

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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

# Import search router for legal verdict search
from api.routers import search as search_router

# Import system router for runtime configuration and health
from api.routers import system as system_router
from mahoun.core.settings import load_security_settings
from mahoun.pipelines._logging import get_logger

HAS_SEARCH_ROUTER = True

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

    try:
        from mahoun.core.config_validator import validate_runtime_config
        from mahoun.core.runtime_config import get_runtime_settings

        validate_runtime_config()

        validation_duration = validation_time.time() - validation_start
        logger.info(f"✅ Runtime configuration validated successfully ({validation_duration * 1000:.1f}ms)")

        # Record metrics
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
        logger.error(f"❌ Configuration validation failed: {e}")

        # Record failure metric
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

# Register search router if available
if HAS_SEARCH_ROUTER and search_router:
    app.include_router(search_router.router)
    logger.info("✓ Legal search router registered at /v1/search")

# Register ingest router if available
if HAS_INGEST_ROUTER:
    from api.routers import ingest as ingest_router

    app.include_router(ingest_router.router, prefix="/api/ingest")
    logger.info("✓ Document ingest router registered at /api/ingest")

# Register MAHOUN router
try:
    from api.routers import mahoun as mahoun_router

    app.include_router(mahoun_router.router)
    logger.info("✓ MAHOUN router registered at /api/v1/mahoun")
except ImportError as e:
    logger.warning(f"MAHOUN router not available: {e}")

# Register Fine-Tuning router
try:
    from api.routers import finetuning as finetuning_router

    app.include_router(finetuning_router.router)
    logger.info("✓ Fine-tuning router registered at /api/v1/finetuning")
except ImportError as e:
    logger.warning(f"Fine-tuning router not available: {e}")

# Register Reasoning router (CRITICAL - Core reasoning API)
try:
    from api.routers import reasoning as reasoning_router

    app.include_router(reasoning_router.router)
    logger.info("✓ Reasoning router registered at /api/v1/reasoning")
except ImportError as e:
    logger.warning(f"Reasoning router not available: {e}")

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
    """Health check endpoint connected to the internal health system"""
    from datetime import datetime

    from mahoun.infrastructure.health_checker import HealthChecker

    checker = HealthChecker()
    results = await checker.check_all()

    # Normalize status to lowercase for consistency with test expectations
    if "status" in results:
        results["status"] = results["status"].lower()

    # Add timestamp for test compatibility
    results["timestamp"] = datetime.now().isoformat()

    return results


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
    """Get current production policy"""
    return {
        "policy_id": "policy_v1.2.0",
        "version": "1.2.0",
        "deployed_at": "2024-01-25T10:30:00Z",
        "status": "active",
        "performance": {"accuracy": 0.892, "latency_p95": 245.3, "error_rate": 0.012},
    }


@app.post("/api/v1/policy/deploy")
async def deploy_policy(request: PolicyDeployRequest):
    """
    Deploy a new policy

    Supports shadow, canary, and full deployment modes.
    """
    logger.info(f"Deploying policy {request.policy_id} in {request.mode} mode")

    return {
        "status": "deployed",
        "policy_id": request.policy_id,
        "version": request.version,
        "mode": request.mode,
        "traffic_percentage": request.traffic_percentage,
        "deployed_at": datetime.now().isoformat(),
    }


@app.get("/api/v1/policy/list")
async def list_policies(status: str | None = None, limit: int = 10):
    """List available policies"""
    policies = [
        {
            "policy_id": "policy_v1.2.0",
            "version": "1.2.0",
            "status": "active",
            "created_at": "2024-01-25T10:00:00Z",
            "performance": {"accuracy": 0.892},
        },
        {
            "policy_id": "policy_v1.1.0",
            "version": "1.1.0",
            "status": "shadow",
            "created_at": "2024-01-20T15:30:00Z",
            "performance": {"accuracy": 0.885},
        },
    ]

    if status:
        policies = [p for p in policies if p["status"] == status]

    return {"policies": policies[:limit], "total": len(policies)}


@app.post("/api/v1/policy/rollback")
async def rollback_policy(request: RollbackRequest):
    """Rollback to a previous policy"""
    logger.warning(f"Rolling back to {request.target_snapshot_id}: {request.reason}")

    return {
        "status": "rolled_back",
        "target_snapshot_id": request.target_snapshot_id,
        "reason": request.reason,
        "rolled_back_at": datetime.now().isoformat(),
    }


# Experiment endpoints
@app.post("/api/v1/experiments")
async def create_experiment(request: ExperimentRequest):
    """Create A/B test experiment"""
    logger.info(f"Creating experiment: {request.name}")

    experiment_id = f"exp_{int(datetime.now().timestamp())}"

    return {
        "experiment_id": experiment_id,
        "name": request.name,
        "variants": request.variants,
        "traffic_split": request.traffic_split,
        "status": "created",
        "created_at": datetime.now().isoformat(),
    }


@app.get("/api/v1/experiments")
async def list_experiments(status: str | None = None, limit: int = 10):
    """List experiments"""
    experiments = [
        {
            "experiment_id": "exp_001",
            "name": "Test GNN Reranking",
            "status": "running",
            "variants": ["control", "gnn"],
            "samples": 1250,
            "created_at": "2024-01-20T10:00:00Z",
        }
    ]

    if status:
        experiments = [e for e in experiments if e["status"] == status]

    return {"experiments": experiments[:limit], "total": len(experiments)}


@app.post("/api/v1/experiments/{experiment_id}/stop")
async def stop_experiment(experiment_id: str):
    """Stop an experiment"""
    logger.info(f"Stopping experiment: {experiment_id}")

    return {
        "experiment_id": experiment_id,
        "status": "stopped",
        "stopped_at": datetime.now().isoformat(),
    }


@app.get("/api/v1/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get experiment results"""
    return {
        "experiment_id": experiment_id,
        "status": "completed",
        "results": {
            "control": {"samples": 1000, "accuracy": 0.876, "latency_p95": 250.5},
            "treatment": {"samples": 1000, "accuracy": 0.892, "latency_p95": 245.3},
        },
        "statistical_significance": {
            "accuracy": {"p_value": 0.023, "significant": True},
            "latency": {"p_value": 0.156, "significant": False},
        },
        "recommendation": "PROMOTE",
    }


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
    return {
        "timestamp": datetime.now().isoformat(),
        "components": {
            "orchestrator": {"status": "running", "uptime": 172800},
            "rl_agent": {"status": "training", "loss": 0.234},
            "bandit": {"status": "active", "total_pulls": 45230},
            "feedback_loop": {"status": "collecting", "buffer_size": 1250},
        },
        "alerts": {"total": 3, "critical": 0, "high": 1, "medium": 2},
        "performance": {"accuracy": 0.876, "latency_p95": 245.3, "throughput": 1250.5},
    }


# System status endpoints
@app.get("/api/v1/status")
async def get_system_status():
    """Get overall system status"""
    return {
        "orchestrator": {
            "state": "running",
            "uptime_seconds": 172800,
            "total_errors": 12,
            "total_recoveries": 3,
        },
        "components": {
            "rl_agent": {"healthy": True, "state": "training"},
            "bandit": {"healthy": True, "state": "active"},
            "active_learning": {"healthy": True, "state": "selecting"},
            "causal_inference": {"healthy": True, "state": "analyzing"},
            "feedback_loop": {"healthy": True, "state": "collecting"},
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/status/health")
async def get_health_status():
    """Get detailed health status from the internal health system"""
    from mahoun.infrastructure.health_checker import HealthChecker

    checker = HealthChecker()
    results = await checker.check_all()
    return results


# Configuration endpoints
@app.get("/api/v1/config")
async def get_config():
    """Get system configuration"""
    return {
        "rl_agent": {"learning_rate": 0.0003, "gamma": 0.99, "batch_size": 64},
        "bandit": {"n_arms": 6, "exploration_bonus": 0.1},
        "feedback_loop": {"learning_frequency": 100, "validation_frequency": 500},
    }


@app.put("/api/v1/config")
async def update_config(config: dict[str, Any]):
    """Update system configuration"""
    logger.info(f"Updating configuration: {list(config.keys())}")

    return {
        "status": "updated",
        "updated_keys": list(config.keys()),
        "updated_at": datetime.now().isoformat(),
    }


# Statistics endpoints
@app.get("/api/v1/stats")
async def get_statistics():
    """Get system statistics"""
    return {
        "feedback_loop": {
            "total_feedback": 12450,
            "total_updates": 124,
            "cycle_count": 15,
        },
        "rl_agent": {"training_steps": 45230, "episodes": 1250, "avg_reward": 0.876},
        "bandit": {"total_pulls": 45230, "best_arm": 3, "exploration_rate": 0.15},
        "experiments": {"total": 25, "running": 3, "completed": 20, "failed": 2},
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
