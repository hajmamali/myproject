"""
Database Connections
====================
Manages connections to PostgreSQL, Neo4j, and Redis
"""

import asyncpg
import redis.asyncio as aioredis
from typing import Any, Optional
import logging
from functools import lru_cache
from api.config import get_settings, Settings

# Optional Neo4j import
try:
    from neo4j import AsyncGraphDatabase
    HAS_NEO4J = True
except ImportError:
    AsyncGraphDatabase: Optional[Any] = None
    HAS_NEO4J = False

log = logging.getLogger(__name__)

# ============================================================================
# Global Connection Pools (Neo4j driver REMOVED for governance compliance)
# ============================================================================
postgres_pool: Optional[asyncpg.Pool] = None
# neo4j_driver: REMOVED - Use governed connection only via mahoun.graph.neo4j.connection
redis_client: Optional[aioredis.Redis] = None

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
# Neo4j - GOVERNANCE COMPLIANT (No Direct Driver Usage)
# ============================================================================
async def init_neo4j():
    """
    Initialize Neo4j connection through governed path ONLY.
    
    GOVERNANCE COMPLIANCE:
    - Uses mahoun.graph.neo4j.connection.get_connection() 
    - All schema operations go through GovernedNeo4jSession
    - No direct driver creation - prevents bypass of MutationAuthorizationBoundary
    """
    if not HAS_NEO4J:
        log.warning("Neo4j driver not available. Skipping Neo4j initialization.")
        return
    
    try:
        # GOVERNANCE FIX: Use governed connection instead of direct driver
        from mahoun.graph.neo4j.connection import get_connection
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        # Test connection through governance boundary
        connection = get_connection()
        test_result = connection.execute_query("RETURN 1 AS test")
        if test_result and test_result[0].get("test") == 1:
            log.info("✅ Neo4j connection verified through governance boundary")
        
        # Apply schema through governed session (if needed)
        try:
            from mahoun.graph.neo4j.init_schema import apply_schema
            
            # Create governance context for schema operations
            async with GovernanceContextManager.active_context(
                correlation_id="api_database_init_schema",
                actor_id="system_bootstrap"
            ):
                apply_schema()
                log.info("✅ Neo4j schema applied through governed session")
                
        except Exception as e:
            log.warning(f"⚠️ Could not apply Neo4j schema (continuing): {e}")
            
    except Exception as e:
        log.error(f"❌ Failed to initialize governed Neo4j connection: {e}")
        raise


async def close_neo4j():
    """Close Neo4j connection through governed path"""
    try:
        from mahoun.graph.neo4j.connection import close_connection
        close_connection()
        log.info("Neo4j governed connection closed")
    except ImportError:
        log.warning("No governed connection to close")


async def get_neo4j():
    """
    Get Neo4j session through GOVERNED path only.
    
    GOVERNANCE COMPLIANCE:
    - Returns GovernedNeo4jSession instead of raw session
    - All queries must go through MutationAuthorizationBoundary
    - Prevents direct driver bypass
    """
    if not HAS_NEO4J:
        raise RuntimeError("Neo4j driver not installed. Install with: pip install neo4j")
    
    try:
        from mahoun.graph.neo4j.connection import get_connection
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        connection = get_connection()
        
        # For API layer operations, create a basic governance context
        async with GovernanceContextManager.active_context(
            correlation_id="api_database_query",
            actor_id="api_layer"
        ):
            with connection.governed_session(
                correlation_id="api_database_query",
                actor_id="api_layer"
            ) as session:
                yield session
                
    except ImportError as e:
        raise RuntimeError(f"Governed Neo4j connection not available: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to get governed Neo4j session: {e}")


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
    await init_neo4j()
    await init_redis()
    log.info("✅ All database connections initialized")


async def close_db():
    """Close all database connections"""
    await close_postgres()
    await close_neo4j()
    await close_redis()
    log.info("All database connections closed")
