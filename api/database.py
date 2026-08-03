"""
Database Connections
====================
Manages connections to PostgreSQL, Neo4j, and Redis.

Architectural notes
-------------------
* This module is the **canonical** place to acquire/inspect the global
  database pools. The :class:`GraphConnectionState` holder below is the
  **single source of truth** for graph availability at runtime — every
  downstream caller (system router, reasoning router, health checker) MUST
  read from it instead of probing the Neo4j driver directly.

* Neo4j initialization is **fail-soft**: a missing, refused, or
  unauthenticated Neo4j backend must not crash startup. The driver is
  set to ``None`` and :data:`GraphConnectionState` is flipped to
  ``enabled=False / backend="disabled"`` so the rest of the system
  degrades to non-graph mode.

* Driver failures are bounded by an explicit, short handshake timeout
  (``NEO4J_HANDSHAKE_TIMEOUT_SEC``) so a black-holed Neo4j port cannot
  stall the lifespan / health endpoints.
"""

import asyncio
import asyncpg
import os
import redis.asyncio as aioredis
from typing import Any, Optional
import logging
import threading
from functools import lru_cache
from api.config import get_settings, Settings

# Optional Neo4j import
try:
    from neo4j import AsyncGraphDatabase
    from neo4j.exceptions import (
        ServiceUnavailable as _Neo4jServiceUnavailable,
        AuthError as _Neo4jAuthError,
        BoltError as _Neo4jBoltError,
    )
    HAS_NEO4J = True
except ImportError:
    AsyncGraphDatabase: Optional[Any] = None
    _Neo4jServiceUnavailable = _Neo4jAuthError = _Neo4jBoltError = Exception  # type: ignore
    HAS_NEO4J = False

log = logging.getLogger(__name__)

# Handshake timeout for the initial "RETURN 1" against Neo4j. Bounded so a
# unreachable backend cannot stall lifespan startup or /health responses.
NEO4J_HANDSHAKE_TIMEOUT_SEC: float = 2.5

# ============================================================================
# Global Connection Pools
# ============================================================================
postgres_pool: Optional[asyncpg.Pool] = None
neo4j_driver: Optional[AsyncGraphDatabase] = None
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
    """Issue a bounded ``RETURN 1`` against the driver.

    Raises ``asyncio.TimeoutError`` if the driver cannot complete the
    handshake within ``timeout_sec``. Any other driver-level failure
    (connection refused, auth, malformed handshake) propagates as-is.
    
    CRITICAL: Uses governance-aware initialization to eliminate P0-1 bypass vector.
    """
    from mahoun.core.governance.database_init import create_governance_aware_initializer
    
    # Use governance-aware initializer instead of raw driver.session()
    initializer = create_governance_aware_initializer(driver)
    result = await initializer.initialize_with_governance(
        timeout_sec=timeout_sec,
        correlation_id="neo4j_handshake_check"
    )
    
    if not result.success:
        raise RuntimeError(f"Neo4j handshake failed through governance layer: {result}")
    
    logger.debug(f"✅ Neo4j handshake completed via governance (context: {result.governance_context_id})")


async def init_neo4j():
    """Initialize Neo4j driver — graceful degradation on failure.

    Behavior contract (Action Item 2):

    * On any connection / handshake / auth failure, this function emits a
      single ``WARNING`` log line and returns normally (does NOT raise).
    * On failure, :data:`GraphConnectionState` is set to
      ``enabled=False / backend="disabled"`` and ``neo4j_driver`` is left
      as ``None``.
    * On success, :data:`GraphConnectionState` is set to
      ``enabled=True / backend=<resolved>`` and ``neo4j_driver`` is the
      live driver.
    """
    global neo4j_driver

    if not HAS_NEO4J or AsyncGraphDatabase is None:
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

    # Build the driver inside its own try so a misconfigured URI is
    # contained (urllib parse errors, missing port, etc.).
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
            max_connection_lifetime=settings.neo4j_max_connection_lifetime,
            max_connection_pool_size=settings.neo4j_max_connection_pool_size,
            connection_acquisition_timeout=settings.neo4j_connection_timeout,
        )
    except (OSError, ValueError, TypeError) as cfg_err:
        # Misconfiguration / invalid URI. Treat as gracefully as a refused
        # connection so startup never crashes on a missing Neo4j.
        log.warning(
            f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
            f"Reason: invalid driver configuration ({cfg_err})"
        )
        GraphConnectionState.set_unavailable(
            reason=f"invalid_configuration: {cfg_err}",
            uri=uri,
        )
        _update_graph_metric(enabled=False)
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
        await _handshake_neo4j(
            neo4j_driver,
            timeout_sec=NEO4J_HANDSHAKE_TIMEOUT_SEC,
        )
    except (asyncio.TimeoutError,) as t_err:
        log.warning(
            f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
            f"Reason: handshake timeout after {NEO4J_HANDSHAKE_TIMEOUT_SEC}s"
        )
        GraphConnectionState.set_unavailable(
            reason=f"handshake_timeout: {t_err}",
            uri=uri,
        )
        _update_graph_metric(enabled=False)
        # Close whatever the driver managed to construct so we do not
        # leak sockets.
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
        log.warning(
            f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
            f"Reason: {type(conn_err).__name__}: {conn_err}"
        )
        GraphConnectionState.set_unavailable(
            reason=f"{type(conn_err).__name__}: {conn_err}",
            uri=uri,
        )
        _update_graph_metric(enabled=False)
        try:
            await neo4j_driver.close()
        except Exception:
            pass
        neo4j_driver = None
        return
    except Exception as e:  # last-resort safety net
        log.warning(
            f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
            f"Reason: {type(e).__name__}: {e}"
        )
        GraphConnectionState.set_unavailable(
            reason=f"{type(e).__name__}: {e}",
            uri=uri,
        )
        _update_graph_metric(enabled=False)
        try:
            await neo4j_driver.close()
        except Exception:
            pass
        neo4j_driver = None
        return

    # Handshake succeeded. Apply ingestion schema (governed-exempt,
    # documented in the call site above). Each statement is independently
    # try/excepted so an idempotent re-run never aborts startup.
    try:
        from mahoun.switchboard import switchboard

        schema_path = switchboard.get_schema("ingestion")
        if schema_path.endswith('.cypher') and os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                cypher_content = f.read()

            statements = [
                s.strip() for s in cypher_content.split(';')
                if s.strip() and not s.strip().startswith('//')
            ]

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

            log.info(f"✅ Neo4j schema applied from {schema_path}")
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


# NOTE: Historical get_neo4j() / Depends(get_neo4j) session-yielding helper was
# a latent governance bypass (raw neo4j_driver.session() handed to routers).
# It had zero callers in this build (grep across api/, services/, tests/).
# Removed. All Neo4j access must go through mahoun.graph.neo4j.connection:
#   - READS: Neo4jConnection.execute_query() (classification-enforced)
#   - WRITES: Neo4jConnection.governed_session() -> GovernedNeo4jSession
# See AGENTRULES.md / Governance section.
#
# Downstream callers should consult `GraphConnectionState.is_available()`
# before issuing any graph query; otherwise the runtime path is
# Neo4jConnection.execute_query() which routes through the canonical
# mutation boundary.


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
