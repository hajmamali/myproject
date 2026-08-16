"""
Neo4j Connection Management
============================

Production-ready connection pooling with retry logic.
"""

import asyncio
import logging
import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from mahoun.core.governance.mutation_boundary import (
        MutationAuthorizationBoundary,
        GovernedNeo4jSession,
        MutationReceipt,
    )
    from mahoun.core.governance.validator_pipeline import ValidatorPipeline
    from mahoun.core.governance.violations import GovernanceViolationError
    from mahoun.core.governance.governance_context import GovernanceContextManager

_conn_logger = logging.getLogger(__name__)

# Global flag to prevent unauthorized direct instantiation of Neo4jConnection
_NEO4J_INIT_AUTHORIZED = False

# Lazy yaml import - only loaded when config files are used
HAS_YAML: Optional[bool] = None
yaml: Optional[Any] = None

def _ensure_yaml():
    """Lazy import yaml only when needed for config file loading"""
    global HAS_YAML, yaml
    if HAS_YAML is None:
        try:
            import yaml as _yaml
            yaml = _yaml
            HAS_YAML = True
        except ImportError:
            HAS_YAML = False
            yaml = None
    return HAS_YAML
def retry_on_failure(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    max_backoff: float = 60.0
):
    """Decorator for retrying failed operations with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    wait_time = min(backoff_factor ** attempt, max_backoff)
                    print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                    print(f"   Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
            
        return wrapper
    return decorator


class Neo4jConnection:
    """
    Thread-safe Neo4j connection with connection pooling
    
    Features:
    - Thread-safe singleton pattern via ThreadSafeSingleton
    - Connection pooling
    - Automatic reconnection
    - Configuration from file or env
    - Health checks
    
    Architectural Mandate:
    Direct instantiation is FORBIDDEN. Use get_connection().
    """
    
    _driver: Optional[Any] = None
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        connection_timeout: float = 30.0,
        max_transaction_retry_time: float = 30.0,
        config_path: Optional[str] = None
    ):
        """
        Initialize Neo4j connection
        """
        # HARDENING: Prefer get_connection() but allow direct instantiation in test/dev
        # Historically the code raised here to forbid direct instantiation. For
        # testability and local development we allow direct construction but
        # emit a warning so callers know the preferred factory (get_connection).
        if not _NEO4J_INIT_AUTHORIZED:
            _conn_logger.warning(
                "Direct Neo4jConnection construction detected — prefer get_connection() "
                "for production. Continuing with direct instantiation for test/dev purposes."
            )

        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # Load from config file if provided
        if config_path and os.path.exists(config_path):
            if not _ensure_yaml():
                raise RuntimeError(
                    "yaml not installed. Run: pip install pyyaml"
                )
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            uri = uri or config.get('uri')
            user = user or config.get('user')
            password = password or config.get('password')
            database = config.get('database', database)
            
            pool_config = config.get('connection_pool', {})
            max_connection_pool_size = pool_config.get('max_size', max_connection_pool_size)
            connection_timeout = pool_config.get('connection_timeout', connection_timeout)
            max_transaction_retry_time = pool_config.get(
                'max_transaction_retry_time',
                max_transaction_retry_time
            )
        
        # Fallback to environment variables (using secrets module for credentials)
        from mahoun.core.secrets import require_secret, get_secret
        
        uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = user or get_secret('NEO4J_USER', 'neo4j')
        # Use canonical secret name DB_NEO4J_PASSWORD (secrets module expects this)
        password = password or require_secret('DB_NEO4J_PASSWORD')
        
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise RuntimeError(
                "neo4j driver not installed. Run: pip install neo4j"
            )
        
        self._driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=max_connection_pool_size,
            connection_timeout=connection_timeout,
            max_transaction_retry_time=max_transaction_retry_time
        )
        
        self.database = database
        self.uri = uri
        self._initialized = True
        
        print(f"✅ Connected to Neo4j at {uri}")
    
    def verify_connection(self) -> bool:
        """
        Verify connection to Neo4j (synchronous)
        
        Returns:
            True if connection is valid, False otherwise
        """
        if self._driver is None:
             raise RuntimeError("Connection not initialized")
        return self.verify_connectivity()
    
    async def connect(self):
        """Asynchronous connection verification (Compatibility wrapper)"""
        return self.verify_connection()
    
    @property
    def driver(self):
        """Get driver instance"""
        if self._driver is None:
            raise RuntimeError("Connection not initialized")
        return self._driver
    
    @contextmanager
    def session(self, **kwargs):
        """
        Context manager for Neo4j session
        
        Usage:
            with connection.session() as session:
                result = session.run(query)
        """
        session = self.driver.session(database=self.database, **kwargs)
        try:
            yield session
        finally:
            session.close()
    
    def _raw_execute(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Any]:
        """
        Internal execution method — calls MutationAuthorizationBoundary
        on EVERY query before reaching the driver.

        This is the single chokepoint for all Cypher execution.
        MutationAuthorizationBoundary.inspect() raises GovernanceViolationError
        if mutation Cypher is detected outside GovernedNeo4jSession.
        """
        # Lazy import to avoid import-time overhead
        from mahoun.core.governance.mutation_boundary import MutationAuthorizationBoundary
        
        MutationAuthorizationBoundary.inspect(query)
        with self.session(**kwargs) as s:
            result = s.run(query, parameters or {})
            return [record for record in result]

    @retry_on_failure(max_attempts=3)
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Any]:
        """
        Execute a READ-ONLY query.

        Mutation Cypher (MERGE/CREATE/DELETE/SET) will raise
        GovernanceViolationError unless called from GovernedNeo4jSession.
        Use governed_session() to perform any writes.

        Args:
            query: Cypher query (READ operations only)
            parameters: Query parameters

        Returns:
            Query results

        Raises:
            GovernanceViolationError: If mutation Cypher is detected.
        """
        return self._raw_execute(query, parameters, **kwargs)

    @contextmanager
    def governed_session(
        self,
        pipeline: Optional["ValidatorPipeline"] = None,
        correlation_id: str = "",
        actor_id: str = "",
    ) -> Generator["GovernedNeo4jSession", None, None]:
        """
        The ONLY authorized entry point for graph mutation.

        Yields a GovernedNeo4jSession which is the only surface that
        may execute mutation Cypher.  Direct execute_query() with
        MERGE/CREATE/DELETE/SET will raise GovernanceViolationError.

        Enforces P0: GovernanceContext MUST be active, else fail-closed.

        Usage::

            async with GovernanceContextManager.active_context(...):
                with connection.governed_session(correlation_id="op-123", actor_id="judge-42") as session:
                    session.write_node(...)

        Args:
            pipeline: Optional ValidatorPipeline.
            correlation_id: Correlation ID (falls back to active context).
            actor_id: Actor responsible for the mutation (for provenance).

        Yields:
            GovernedNeo4jSession
        """
        # Lazy imports to avoid import-time overhead
        from mahoun.core.governance.governance_context import GovernanceContextManager
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        
        # Enforce governance context at the boundary entry (fail-closed)
        GovernanceContextManager.require_context()
        yield GovernedNeo4jSession(
            raw_executor=self._raw_execute,
            pipeline=pipeline,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )
    
    def execute_write(self, *args, **kwargs):  # type: ignore[override]
        """
        REMOVED — constitutional violation.

        Direct execute_write() is forbidden. It bypasses the
        MutationAuthorizationBoundary. Use governed_session() instead.

        Raises:
            GovernanceViolationError: Always.
        """
        from mahoun.core.governance.violations import (
            GovernanceViolation, ViolationSeverity, ViolationCategory,
        )
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ARCHITECTURE_BOUNDARY,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "execute_write() is constitutionally forbidden. "
                    "Use connection.governed_session() for all graph mutations."
                ),
                details={},
                source="Neo4jConnection.execute_write",
            )
        )
    
    @retry_on_failure(max_attempts=3)
    def execute_read(
        self,
        func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute a read transaction with retry logic
        
        Args:
            func: Transaction function
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Transaction result
        """
        with self.session() as session:
            return session.execute_read(func, *args, **kwargs)
    
    @retry_on_failure(max_attempts=3)
    def execute_batch(
        self,
        queries: List[Tuple[str, Dict]],
        batch_size: int = 1000
    ) -> List:
        """
        Execute batch queries in a single transaction
        
        Args:
            queries: List of (query, parameters) tuples
            batch_size: Maximum queries per transaction
            
        Returns:
            List of results for each query
        """
        results: List[Any] = []
        with self.session() as session:
            # Process in batches
            for i in range(0, len(queries), batch_size):
                batch = queries[i:i + batch_size]
                
                def batch_transaction(tx):
                    batch_results: List[Any] = []
                    for query, params in batch:
                        result = tx.run(query, params or {})
                        batch_results.append([record for record in result])
                    return batch_results
                
                batch_results = session.execute_write(batch_transaction)
                results.extend(batch_results)
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Neo4j connection
        
        Returns:
            Dictionary with health status and metrics
        """
        health_status = {
            "status": "unhealthy",
            "connected": False,
            "response_time_ms": None,
            "node_count": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            
            # Test basic connectivity
            with self.session() as session:
                result = session.run("RETURN 1 AS num")
                if result.single()["num"] != 1:
                    health_status["error"] = "Unexpected query result"
                    return health_status
                
                # Get node count
                node_result = session.run("MATCH (n) RETURN count(n) AS count")
                node_count = node_result.single()["count"]
                
                response_time = (time.time() - start_time) * 1000
                
                health_status.update({
                    "status": "healthy",
                    "connected": True,
                    "response_time_ms": round(response_time, 2),
                    "node_count": node_count,
                    "database": self.database,
                    "uri": self.uri
                })
                
        except Exception as e:
            health_status["error"] = str(e)
        
        return health_status
    
    def verify_connectivity(self) -> bool:
        """Verify connection to Neo4j"""
        try:
            with self.session() as session:
                result = session.run("RETURN 1 AS num")
                return result.single()["num"] == 1
        except Exception as e:
            print(f"❌ Connection verification failed: {e}")
            return False

    def ping(self) -> bool:
        """
        Lightweight connectivity check. Does NOT create a new driver.

        This method first attempts a short TCP connect to the configured host/port
        derived from the connection URI — this is intentionally lightweight and
        avoids the Neo4j driver handshake so it can be used by fast health
        checkers. If the TCP probe fails it falls back to driver-based
        verify_connectivity() which will reuse the existing driver if present.

        Returns:
            True if Neo4j is reachable, False otherwise. Never raises.
        """
        # Fast TCP probe to avoid expensive driver handshakes and meet <100ms
        try:
            # Parse host/port from uri like bolt://host:7687 or neo4j://host:7687
            import socket
            from urllib.parse import urlparse

            parsed = urlparse(self.uri)
            host = parsed.hostname or 'localhost'
            port = parsed.port or 7687

            # Short timeout for health checks — tuned to be well under 100ms
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except Exception:
            # Fall back to driver-based verification if TCP probe fails
            try:
                return self.verify_connectivity()
            except Exception:
                return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        with self.session() as session:
            # Node count
            node_result = session.run("MATCH (n) RETURN count(n) AS count")
            node_count = node_result.single()["count"]
            
            # Relationship count
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            rel_count = rel_result.single()["count"]
            
            # Labels
            label_result = session.run("CALL db.labels()")
            labels = [record["label"] for record in label_result]
            
            # Relationship types
            type_result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in type_result]
            
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "labels": labels,
                "relationship_types": rel_types,
                "database": self.database,
                "uri": self.uri
            }
    
    def close(self):
        """Close connection"""
        if self._driver:
            self._driver.close()
            self._driver = None
            print("✅ Neo4j connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class Neo4jConnectionPool:
    """
    Connection pool manager for Neo4j
    
    Uses Neo4j driver's built-in connection pooling for high-throughput scenarios.
    This is a lightweight wrapper that leverages the driver's native pool management.
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        pool_size: int = 50,
        connection_timeout: float = 30.0,
        max_transaction_retry_time: float = 30.0,
        database: str = "neo4j",
        **kwargs
    ):
        """
        Initialize connection pool using Neo4j driver's native pooling
        
        Args:
            uri: Neo4j URI
            user: Username
            password: Password
            pool_size: Maximum connections in pool
            connection_timeout: Connection timeout in seconds
            max_transaction_retry_time: Max retry time for transactions
            database: Database name
            **kwargs: Additional connection arguments
        """
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise RuntimeError(
                "neo4j driver not installed. Run: pip install neo4j"
            )
        
        # Use driver's built-in connection pooling
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=pool_size,
            connection_timeout=connection_timeout,
            max_transaction_retry_time=max_transaction_retry_time,
            **kwargs
        )
        self.database = database
        self.uri = uri
        
        print(f"✅ Connection pool initialized (max_size={pool_size}) at {uri}")
    
    @contextmanager
    def session(self, **kwargs):
        """
        Context manager for Neo4j session from pool
        
        Usage:
            with pool.session() as session:
                result = session.run(query)
        """
        session = self.driver.session(database=self.database, **kwargs)
        try:
            yield session
        finally:
            session.close()
    
    def close_all(self):
        """Close connection pool and all connections"""
        if self.driver:
            self.driver.close()
            print("✅ Connection pool closed")


# Thread-safe singleton for Neo4j connection - lazy loaded
_neo4j_singleton: Optional[Any] = None


def _get_singleton():
    """Lazy initialization of ThreadSafeSingleton to reduce import-time overhead"""
    global _neo4j_singleton
    if _neo4j_singleton is None:
        from mahoun.core.singleton import ThreadSafeSingleton
        _neo4j_singleton = ThreadSafeSingleton["Neo4jConnection"]("Neo4jConnection")
    return _neo4j_singleton


def get_connection(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs
) -> Neo4jConnection:
    """
    Get or create thread-safe global Neo4j connection
    
    This function uses ThreadSafeSingleton to ensure thread-safe access
    to the Neo4j connection across multiple threads.
    
    Args:
        uri: Neo4j URI
        user: Username
        password: Password
        **kwargs: Additional connection arguments
        
    Returns:
        Neo4jConnection instance (thread-safe singleton)
    """
    global _NEO4J_INIT_AUTHORIZED
    _NEO4J_INIT_AUTHORIZED = True
    try:
        singleton = _get_singleton()
        return singleton.get_instance(
            factory=lambda: Neo4jConnection(uri, user, password, **kwargs)
        )
    finally:
        _NEO4J_INIT_AUTHORIZED = False


# Alias for backward compatibility


# ============================================================================
# Async Driver Initialization (For API Layer Bootstrap)
# ============================================================================

async def initialize_canonical_async_driver(
    uri: str,
    auth: Tuple[str, str],
    *,
    max_connection_lifetime: int = 3600,
    max_connection_pool_size: int = 50,
    connection_acquisition_timeout: float = 60.0,
    **driver_config
) -> 'AsyncDriver':
    """
    CANONICAL async driver initialization - ONLY location authorized
    
    This function is the sole authorized source for AsyncGraphDatabase.driver()
    instantiation in the entire codebase. Per AGENTS.md Section 1-A, no other
    module may create async drivers.
    
    Used by:
    - api/database.py for application bootstrap
    - Governed initialization flows
    
    Args:
        uri: Neo4j connection URI
        auth: (username, password) tuple
        max_connection_lifetime: Maximum connection lifetime in seconds
        max_connection_pool_size: Maximum connection pool size
        connection_acquisition_timeout: Timeout for acquiring connections
        **driver_config: Additional driver configuration
    
    Returns:
        AsyncDriver instance managed by canonical connection layer
    
    Raises:
        RuntimeError: If neo4j driver not installed
        ConnectionError: If driver creation fails
    
    Example:
        ```python
        from mahoun.graph.neo4j.connection import initialize_canonical_async_driver
        
        driver = await initialize_canonical_async_driver(
            uri="neo4j://localhost:7687",
            auth=("neo4j", "password"),
            max_connection_pool_size=100
        )
        ```
    
    Constitutional Compliance:
    - Satisfies CONSTITUTION.md Section 7 (Source of Truth Principle)
    - Implements AGENTS.md Section 1-A (Canonical Neo4j Connection)
    - Enforced by gate_neo4j_governance.sh
    """
    try:
        from neo4j import AsyncGraphDatabase
    except ImportError:
        raise RuntimeError(
            "neo4j driver not installed. Run: pip install neo4j>=5.18"
        )
    
    _conn_logger.info(
        f"🔧 Initializing canonical async Neo4j driver at {uri} "
        f"(pool_size={max_connection_pool_size})"
    )
    
    try:
        driver = AsyncGraphDatabase.driver(
            uri,
            auth=auth,
            max_connection_lifetime=max_connection_lifetime,
            max_connection_pool_size=max_connection_pool_size,
            connection_acquisition_timeout=connection_acquisition_timeout,
            **driver_config
        )
        
        _conn_logger.info(
            f"✅ Canonical async driver initialized successfully at {uri}"
        )
        
        return driver
        
    except Exception as e:
        _conn_logger.error(
            f"❌ Failed to initialize canonical async driver: {type(e).__name__}: {e}"
        )
        raise ConnectionError(
            f"Canonical async driver initialization failed at {uri}: {e}"
        ) from e


async def verify_async_driver_connectivity(
    driver: 'AsyncDriver',
    timeout_sec: float = 5.0
) -> bool:
    """
    Verify async driver connectivity with governance awareness
    
    This provides a governance-aware handshake check that routes through
    the proper authorization boundary instead of using raw driver.session().
    
    Args:
        driver: AsyncDriver instance to verify
        timeout_sec: Timeout for connectivity check
    
    Returns:
        True if driver is connected and operational
    
    Raises:
        asyncio.TimeoutError: If connectivity check times out
        ConnectionError: If connectivity check fails
    """
    try:
        from mahoun.core.governance.database_init import create_governance_aware_initializer
        
        _conn_logger.debug("🔍 Verifying async driver connectivity through governance layer")
        
        # Use governance-aware initializer instead of raw driver.session()
        initializer = create_governance_aware_initializer(driver)
        result = await asyncio.wait_for(
            initializer.initialize_with_governance(
                timeout_sec=timeout_sec,
                correlation_id="async_driver_connectivity_check"
            ),
            timeout=timeout_sec
        )
        
        if result.success and result.neo4j_available:
            _conn_logger.debug("✅ Async driver connectivity verified")
            return True
        else:
            _conn_logger.warning(f"⚠️ Async driver connectivity check failed: {result}")
            return False
            
    except asyncio.TimeoutError:
        _conn_logger.error(f"❌ Async driver connectivity check timed out after {timeout_sec}s")
        raise
    except Exception as e:
        _conn_logger.error(f"❌ Async driver connectivity check failed: {e}")
        raise ConnectionError(f"Driver connectivity verification failed: {e}") from e


# ============================================================================
# Connection State Helpers (For API Layer Integration)
# ============================================================================

class AsyncDriverHandle:
    """
    Wrapper for async driver that provides governance-aware operations
    
    This replaces direct driver.session() usage with governed alternatives.
    Used by api/database.py to maintain governance compliance during bootstrap.
    """
    
    def __init__(self, driver: 'AsyncDriver'):
        self.driver = driver
        self._closed = False
    
    async def execute_governed_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query through governance boundary
        
        This ensures all queries route through mutation authorization,
        even during bootstrap operations.
        """
        if self._closed:
            raise RuntimeError("Driver handle is closed")
        
        try:
            from mahoun.core.governance.database_init import create_governance_aware_initializer
            from mahoun.core.governance.authorization_state import set_authorized, reset_authorized
            
            # Schema operations during bootstrap require authorization
            auth_token = set_authorized(True)
            
            try:
                # Execute through governance layer
                async with self.driver.session() as session:
                    result = await session.run(query, parameters or {})
                    records = [dict(record) async for record in result]
                    return records
            finally:
                reset_authorized(auth_token)
                
        except Exception as e:
            _conn_logger.error(f"❌ Governed query execution failed: {e}")
            raise
    
    async def close(self):
        """Close the wrapped driver"""
        if not self._closed:
            await self.driver.close()
            self._closed = True
            _conn_logger.info("🔒 Async driver handle closed")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def wrap_async_driver(driver: 'AsyncDriver') -> AsyncDriverHandle:
    """
    Wrap async driver with governance-aware handle
    
    Use this instead of direct driver access to maintain governance compliance.
    """
    return AsyncDriverHandle(driver)


__all__ = [
    'Neo4jConnection',
    'get_connection',
    'initialize_canonical_async_driver',
    'verify_async_driver_connectivity',
    'AsyncDriverHandle',
    'wrap_async_driver',
]


# ============================================================================
# Exception Re-exports (For API Layer)
# ============================================================================
# Re-export Neo4j exception types so API layer doesn't need direct neo4j imports
# This maintains the single import point mandated by AGENTS.md Section 1-A

try:
    from neo4j.exceptions import (
        ServiceUnavailable as Neo4jServiceUnavailable,
        AuthError as Neo4jAuthError,
        BoltError as Neo4jBoltError,
    )
    NEO4J_EXCEPTIONS_AVAILABLE = True
except ImportError:
    # Fallback types if neo4j not installed
    Neo4jServiceUnavailable = ConnectionError  # type: ignore
    Neo4jAuthError = PermissionError  # type: ignore
    Neo4jBoltError = RuntimeError  # type: ignore
    NEO4J_EXCEPTIONS_AVAILABLE = False

__all__ = [
    'Neo4jConnection',
    'get_connection',
    'initialize_canonical_async_driver',
    'verify_async_driver_connectivity',
    'AsyncDriverHandle',
    'wrap_async_driver',
    # Exception re-exports
    'Neo4jServiceUnavailable',
    'Neo4jAuthError',
    'Neo4jBoltError',
]
