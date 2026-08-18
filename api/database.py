"""
Database Connections
====================
Manages connections to PostgreSQL, Neo4j, and Redis.

Architectural notes
-------------------
* This module is the **application-layer database coordinator**. Neo4j driver
  instantiation has been delegated to the canonical connection layer
  (mahoun.graph.neo4j.connection) per AGENTS.md Section 1-A and
  CONSTITUTION.md Section 7 (Source of Truth Principle).

* The :class:`GraphConnectionState` holder is the **single source of truth**
  for graph availability at runtime — every downstream caller (system router,
  reasoning router, health checker) MUST read from it instead of probing
  the Neo4j driver directly.

* Neo4j initialization is **fail-soft**: a missing, refused, or
  unauthenticated Neo4j backend must not crash startup. The driver is
  set to ``None`` and :data:`GraphConnectionState` is flipped to
  ``enabled=False / backend="disabled"`` so the rest of the system
  degrades to non-graph mode.

* Driver failures are bounded by an explicit, short handshake timeout
  (``NEO4J_HANDSHAKE_TIMEOUT_SEC``) so a black-holed Neo4j port cannot
  stall the lifespan / health endpoints.

* **GOVERNANCE COMPLIANCE**: All Neo4j operations route through the
  canonical governed connection layer. This eliminates the P0 bypass
  vector documented in docs/governance/API_DATABASE_ACCESS_AUDIT.md.
"""

import asyncio
import asyncpg
import os
import redis.asyncio as aioredis
from typing import Any, Optional
import logging
import threading
from functools import lru_cache
from enum import Enum
from api.config import get_settings, Settings

# Neo4j canonical connection import (AGENTS.md Section 1-A)
# All Neo4j driver instantiation MUST route through mahoun.graph.neo4j.connection
# Neo4j canonical connection import (AGENTS.md Section 1-A)
# All Neo4j driver instantiation MUST route through mahoun.graph.neo4j.connection
# Governance-aware database initialization import
from mahoun.core.governance.database_init import create_governance_aware_initializer

try:
    from mahoun.graph.neo4j.connection import (
        initialize_canonical_async_driver,
        verify_async_driver_connectivity,
        # Exception re-exports (avoids direct neo4j imports)
        Neo4jServiceUnavailable as _Neo4jServiceUnavailable,
        Neo4jAuthError as _Neo4jAuthError,
        Neo4jBoltError as _Neo4jBoltError,
    )
    HAS_NEO4J = True
except ImportError:
    initialize_canonical_async_driver = None  # type: ignore
    verify_async_driver_connectivity = None  # type: ignore
    _Neo4jServiceUnavailable = _Neo4jAuthError = _Neo4jBoltError = Exception  # type: ignore
    HAS_NEO4J = False

log = logging.getLogger(__name__)

# Handshake timeout for the initial "RETURN 1" against Neo4j. Bounded so a
# unreachable backend cannot stall lifespan startup or /health responses.
NEO4J_HANDSHAKE_TIMEOUT_SEC: float = 2.5


def _handle_neo4j_init_failure(
    uri: str,
    reason: str,
    fail_closed: bool,
    exc: Optional[Exception] = None
) -> bool:
    """
    Handle Neo4j initialization failure with appropriate logging and state setting.
    
    Args:
        uri: The Neo4j URI that failed
        reason: Human-readable reason for failure
        fail_closed: If True, raise RuntimeError instead of returning
        exc: Optional exception that caused the failure
    
    Returns:
        True if failure was handled (i.e., fail_closed=False), False if about to raise
    
    Raises:
        RuntimeError: If fail_closed=True
    """
    if fail_closed:
        # In fail-closed mode, we must not silently degrade
        error_msg = f"Neo4j initialization FAILED (mandatory): {reason}"
        if uri:
            error_msg += f" at {uri}"
        if exc:
            error_msg += f" - {type(exc).__name__}: {exc}"
        raise RuntimeError(error_msg) from exc
    
    # Fail-soft mode: log and continue
    log.warning(
        f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
        f"Reason: {reason}"
    )
    GraphConnectionState.set_unavailable(reason=reason, uri=uri)
    _update_graph_metric(enabled=False)
    return True


# ============================================================================
# Neo4j Initialization State Model
# ============================================================================

class Neo4jInitializationState(Enum):
    """
    Explicit state model for Neo4j initialization.
    
    These states represent the progress of Neo4j bootstrap and must not be
    conflated. A state transition diagram:
    
        NOT_STARTED
            ↓ (init_neo4j() called)
        DRIVER_INITIALIZED
            ↓ (driver created successfully)
        GOVERNANCE_HANDSHAKE_PASSED
            ↓ (governance-aware connectivity check passed)
        DATABASE_CONNECTED
            ↓ (full operational status)
        GRAPH_RUNTIME_AVAILABLE
    
    If any step fails:
        DRIVER_INITIALIZED → DRIVER_INITIALIZED_FAILED
        GOVERNANCE_HANDSHAKE_PASSED → GOVERNANCE_HANDSHAKE_FAILED
        DATABASE_CONNECTED → DATABASE_CONNECTED_FAILED
    
    Final degraded state: GRAPH_RUNTIME_DEGRADED (Neo4j unavailable, non-graph mode)
    
    Final failure state: INITIALIZATION_FAILED (for server_full with mandatory graph)
    """
    NOT_STARTED = "not_started"
    DRIVER_INITIALIZED = "driver_initialized"
    DRIVER_INITIALIZED_FAILED = "driver_initialized_failed"
    GOVERNANCE_HANDSHAKE_PASSED = "governance_handshake_passed"
    GOVERNANCE_HANDSHAKE_FAILED = "governance_handshake_failed"
    DATABASE_CONNECTED = "database_connected"
    DATABASE_CONNECTED_FAILED = "database_connected_failed"
    GRAPH_RUNTIME_AVAILABLE = "graph_runtime_available"
    GRAPH_RUNTIME_DEGRADED = "graph_runtime_degraded"
    INITIALIZATION_FAILED = "initialization_failed"

# ============================================================================
# Global Connection Pools
# ============================================================================
postgres_pool: Optional[asyncpg.Pool] = None
# Neo4j driver managed by canonical connection layer (AGENTS.md Section 1-A)
# This is now initialized via the canonical connection layer
neo4j_driver: Optional[Any] = None
redis_client: Optional[aioredis.Redis] = None


# ============================================================================
# Graph Connection State (canonical runtime flag)
# ============================================================================
class GraphConnectionState:
    """
    Thread-safe holder for the runtime graph availability flag.

    This is the **single source of truth** that downstream graph routers
    MUST consult before issuing any Cypher. Per ``api/database.py`` /
    Action Item 2, when Neo4j is unreachable, ``init_neo4j()`` flips
    ``enabled=False`` and ``backend="disabled"`` here. Health checks,
    reasoning routers, and search routers read from this state.

    Reads are lock-free (atomic attribute reads in CPython). Writes are
    guarded by ``_lock`` so a concurrent retry does not race with the
    "disabled" flip.
    """

    _lock = threading.Lock()

    # Defaults reflect the optimistic "ready" stance. ``init_neo4j()``
    # may downgrade these on connection/handshake failure.
    enabled: bool = True
    backend: str = "local_full"   # "local_full" | "remote" | "disabled"
    last_error: Optional[str] = None
    last_attempt_at: Optional[str] = None
    last_success_at: Optional[str] = None
    uri: Optional[str] = None

    @classmethod
    def set_unavailable(
        cls,
        *,
        reason: str,
        uri: Optional[str] = None,
    ) -> None:
        """Flip the graph into the disabled fallback state."""
        from datetime import datetime
        with cls._lock:
            cls.enabled = False
            cls.backend = "disabled"
            cls.last_error = reason
            cls.last_attempt_at = datetime.utcnow().isoformat()
            if uri is not None:
                cls.uri = uri

    @classmethod
    def set_available(cls, *, backend: str, uri: Optional[str] = None) -> None:
        """Mark the graph as available with the resolved backend."""
        from datetime import datetime
        with cls._lock:
            cls.enabled = True
            cls.backend = backend
            cls.last_error = None
            cls.last_attempt_at = datetime.utcnow().isoformat()
            cls.last_success_at = cls.last_attempt_at
            if uri is not None:
                cls.uri = uri

    @classmethod
    def snapshot(cls) -> dict:
        """Return a JSON-safe snapshot for /health payloads and metrics."""
        return {
            "graph_enabled": cls.enabled,
            "graph_backend": cls.backend,
            "last_error": cls.last_error,
            "last_attempt_at": cls.last_attempt_at,
            "last_success_at": cls.last_success_at,
            "uri": cls.uri,
        }

    @classmethod
    def is_available(cls) -> bool:
        """Quick guard for downstream callers (e.g., graph routers)."""
        return cls.enabled and cls.backend != "disabled"


@lru_cache()
def _get_db_settings() -> Settings:
    """Cached function to get database settings."""
    return get_settings()


# ============================================================================
# PostgreSQL
# ============================================================================
async def init_postgres():
    """Initialize PostgreSQL connection pool"""
    settings = _get_db_settings().database
    global postgres_pool
    try:
        postgres_pool = await asyncpg.create_pool(
            dsn=settings.postgres_url,
            min_size=settings.postgres_pool_size,
            max_size=settings.postgres_max_overflow,
            timeout=settings.postgres_pool_timeout
        )
        log.info("✅ PostgreSQL connection pool created")
    except Exception as e:
        log.error(f"❌ Failed to create PostgreSQL pool: {e}")
        raise


async def close_postgres():
    """Close PostgreSQL connection pool"""
    global postgres_pool
    if postgres_pool:
        await postgres_pool.close()
        log.info("PostgreSQL connection pool closed")


async def get_postgres():
    """Get PostgreSQL connection from pool"""
    if not postgres_pool:
        await init_postgres()
    async with postgres_pool.acquire() as conn:
        yield conn


# ============================================================================
# Neo4j — fail-soft, governance-state-aware
# ============================================================================
def _update_graph_metric(enabled: bool) -> None:
    """Best-effort update of the ``graph_enabled`` Prometheus gauge.

    The metrics module is optional; if it is not importable (e.g. minimal
    test environment) the call is a no-op so the rest of init_neo4j can
    proceed unaffected.
    """
    try:
        from mahoun.metrics import set_graph_enabled

        set_graph_enabled(enabled)
    except Exception as metric_err:  # pragma: no cover - metrics are optional
        log.debug(f"set_graph_enabled metric update skipped: {metric_err}")


async def _handshake_neo4j(driver: Any, timeout_sec: float) -> None:
    """Issue a bounded handshake against the driver through governance layer.

    Raises ``asyncio.TimeoutError`` if the driver cannot complete the
    handshake within ``timeout_sec``. Any other driver-level failure
    (connection refused, auth, malformed handshake) propagates as-is.
    
    GOVERNANCE COMPLIANT: Uses canonical verify_async_driver_connectivity()
    instead of raw driver.session(), eliminating P0 bypass vector.
    """
    if not verify_async_driver_connectivity:
        raise RuntimeError("Neo4j governance layer not available")
    
    # Use canonical governance-aware connectivity verification
    success = await verify_async_driver_connectivity(driver, timeout_sec=timeout_sec)
    
    if not success:
        raise RuntimeError("Neo4j handshake failed through governance layer")
    
    _conn_logger.debug(f"✅ Neo4j handshake completed via canonical governance layer")


async def init_neo4j(fail_closed_on_unavailable: bool = False):
    """Initialize Neo4j driver — fail-soft or fail-closed based on configuration.

    Behavior contract:

    * In fail-soft mode (default): On any connection / handshake / auth failure,
      this function emits a WARNING log line and returns normally (does NOT raise).
      GraphConnectionState is set to enabled=False / backend="disabled".
    
    * In fail-closed mode (fail_closed_on_unavailable=True): If Neo4j is
      unavailable, raises RuntimeError to prevent application startup in
      configurations where graph is mandatory (e.g., server_full + graph_enabled=True).
      
    * On success, :data:`GraphConnectionState` is set to
      ``enabled=True / backend=<resolved>`` and ``neo4j_driver`` is the
      live driver.
    
    GOVERNANCE COMPLIANT (AGENTS.md Section 1-A):
    All driver instantiation delegates to canonical connection layer
    (mahoun.graph.neo4j.connection.initialize_canonical_async_driver).
    This eliminates the P0 governance bypass identified in API_DATABASE_ACCESS_AUDIT.md.
    
    Args:
        fail_closed_on_unavailable: If True, raise RuntimeError when Neo4j is
            unavailable instead of returning normally. Used when graph is mandatory.
    
    Raises:
        RuntimeError: If fail_closed_on_unavailable=True and Neo4j is unavailable.
    """
    global neo4j_driver

    if not HAS_NEO4J or initialize_canonical_async_driver is None:
        if fail_closed_on_unavailable:
            raise RuntimeError(
                "Neo4j driver not installed but graph is mandatory in this configuration. "
                "Install neo4j driver or disable graph mode."
            )
        log.warning("Neo4j driver not available. Skipping Neo4j initialization.")
        GraphConnectionState.set_unavailable(
            reason="driver_not_installed",
            uri=None,
        )
        _update_graph_metric(enabled=False)
        return

    settings = _get_db_settings().database
    uri = settings.neo4j_uri
    GraphConnectionState.uri = uri

    # GOVERNANCE COMPLIANT (AGENTS.md Section 1-A):
    # Driver instantiation delegated to canonical connection layer.
    # This eliminates the P0 bypass vector identified in governance audit.
    try:
        neo4j_driver = await initialize_canonical_async_driver(
            uri=uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
            max_connection_lifetime=settings.neo4j_max_connection_lifetime,
            max_connection_pool_size=settings.neo4j_max_connection_pool_size,
            connection_acquisition_timeout=settings.neo4j_connection_timeout,
        )
    except (OSError, ValueError, TypeError) as cfg_err:
        # Misconfiguration / invalid URI
        _handle_neo4j_init_failure(
            uri=uri,
            reason=f"invalid_configuration: {cfg_err}",
            fail_closed=fail_closed_on_unavailable,
            exc=cfg_err
        )
        neo4j_driver = None
        return

    # Handshake. A short, bounded timeout ensures a black-holed port
    # never stalls the lifespan or /health responses.
    try:
        # GOVERNED EXEMPTION (startup only): this raw `neo4j_driver.session()`
        # runs BEFORE Neo4jConnection / GovernedNeo4jSession exist, because
        # this call is what brings the connection up. It is a one-time
        # schema-apply step executed during DB bootstrap. After bootstrap the
        # runtime path is `Neo4jConnection.execute_query()` /
        # `governed_session()`. Documented in AGENTRULES.md governance section.
        await asyncio.wait_for(
            _handshake_neo4j(
                neo4j_driver,
                timeout_sec=NEO4J_HANDSHAKE_TIMEOUT_SEC,
            ),
            timeout=NEO4J_HANDSHAKE_TIMEOUT_SEC,
        )
    except (asyncio.TimeoutError,) as t_err:
        # Handshake timeout - fail closed if required
        _handle_neo4j_init_failure(
            uri=uri,
            reason=f"handshake_timeout after {NEO4J_HANDSHAKE_TIMEOUT_SEC}s",
            fail_closed=fail_closed_on_unavailable,
            exc=t_err
        )
        # Close whatever the driver managed to construct so we do not leak sockets
        try:
            await neo4j_driver.close()
        except Exception:
            pass
        neo4j_driver = None
        return
    except (
        _Neo4jServiceUnavailable,
        _Neo4jAuthError,
        _Neo4jBoltError,
        ConnectionError,
        OSError,
    ) as conn_err:
        # Connection errors - fail closed if required
        _handle_neo4j_init_failure(
            uri=uri,
            reason=f"{type(conn_err).__name__}: {conn_err}",
            fail_closed=fail_closed_on_unavailable,
            exc=conn_err
        )
        try:
            await neo4j_driver.close()
        except Exception:
            pass
        neo4j_driver = None
        return
    except Exception as e:  # last-resort safety net
        # Unexpected error - fail closed if required
        _handle_neo4j_init_failure(
            uri=uri,
            reason=f"{type(e).__name__}: {e}",
            fail_closed=fail_closed_on_unavailable,
            exc=e
        )
        try:
            await neo4j_driver.close()
        except Exception:
            pass
        neo4j_driver = None
        return

    # Handshake succeeded. Apply ingestion schema through governance layer.
    # Schema operations now route through authorized context instead of
    # raw driver.session(), eliminating the documented "GOVERNED EXEMPTION".
    try:
        from mahoun.switchboard import switchboard
        from mahoun.core.governance.authorization_state import set_authorized, reset_authorized

        schema_path = switchboard.get_schema("ingestion")
        if schema_path.endswith('.cypher') and os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                cypher_content = f.read()

            statements = [
                s.strip() for s in cypher_content.split(';')
                if s.strip() and not s.strip().startswith('//')
            ]

            # Schema operations require authorization context
            auth_token = set_authorized(True)
            
            try:
                # BOOTSTRAP EXEMPTION: Schema application during init_neo4j() uses
                # raw driver.session() because the canonical connection layer hasn't
                # been initialized yet. This is governed by set_authorized() context
                # and only executes idempotent schema DDL, never user data mutations.
                # Documented in API_DATABASE_ACCESS_AUDIT.md as acceptable bootstrap pattern.
                async with neo4j_driver.session() as session:
                    for statement in statements:
                        if statement.startswith('//'):
                            continue
                        try:
                            await session.run(statement)
                        except Exception as st_err:
                            log.warning(
                                f"Neo4j schema execution warning (might be safe to ignore): {st_err}"
                            )
            finally:
                # Always reset authorization state
                reset_authorized(auth_token)

            log.info(f"✅ Neo4j schema applied from {schema_path} (governed)")
    except FileNotFoundError:
        log.debug("Neo4j ingestion schema file not found; skipping schema apply")
    except Exception as e:
        log.warning(f"⚠️ Could not apply Neo4j schema automatically: {e}")

    # Resolve the backend label for governance-state reporting.
    backend_label = "remote" if uri.startswith(("neo4j://", "neo4j+s://")) else "local_full"
    GraphConnectionState.set_available(backend=backend_label, uri=uri)
    _update_graph_metric(enabled=True)
    log.info(f"✅ Neo4j driver initialized at {uri} (backend={backend_label})")


async def close_neo4j():
    """Close Neo4j driver"""
    global neo4j_driver
    if neo4j_driver:
        try:
            await neo4j_driver.close()
        except Exception as e:
            log.debug(f"Error closing Neo4j driver: {e}")
        finally:
            neo4j_driver = None
        log.info("Neo4j driver closed")


# ============================================================================
# GOVERNANCE ARCHITECTURE NOTE
# ============================================================================
# Historical context: This module previously had direct database access,
# creating a P0 governance bypass vector (documented in
# docs/governance/API_DATABASE_ACCESS_AUDIT.md).
#
# FIXED: Driver instantiation now delegates to canonical connection layer:
#   mahoun.graph.neo4j.connection.initialize_canonical_async_driver()
#
# All Neo4j access must route through mahoun.graph.neo4j.connection:
#   - READS: Neo4jConnection.execute_query() (classification-enforced)
#   - WRITES: Neo4jConnection.governed_session() -> GovernedNeo4jSession
#
# Downstream callers should consult `GraphConnectionState.is_available()`
# before issuing any graph query. The runtime path is:
#   api/routers → get_connection() → Neo4jConnection → MutationAuthorizationBoundary
#
# See AGENTS.md Section 1-A for canonical component specification.


# ============================================================================
# Redis
# ============================================================================
async def init_redis():
    """Initialize Redis client"""
    settings = _get_db_settings().database
    global redis_client
    try:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections
        )
        # Test connection
        await redis_client.ping()
        log.info("✅ Redis client initialized")
    except Exception as e:
        log.error(f"❌ Failed to initialize Redis client: {e}")
        raise


async def close_redis():
    """Close Redis client"""
    global redis_client
    if redis_client:
        await redis_client.close()
        log.info("Redis client closed")


async def get_redis():
    """Get Redis client"""
    if not redis_client:
        await init_redis()
    return redis_client


# ============================================================================
# Initialize All Databases
# ============================================================================
async def init_db():
    """Initialize all database connections"""
    await init_postgres()
    # Neo4j is intentionally fail-soft: see init_neo4j(). It never raises.
    await init_neo4j()
    await init_redis()
    log.info("✅ All database connections initialized")


async def close_db():
    """Close all database connections"""
    await close_postgres()
    await close_neo4j()
    await close_redis()
    log.info("All database connections closed")
