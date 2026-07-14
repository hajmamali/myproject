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
# Global Connection Pools
# ============================================================================
postgres_pool: Optional[asyncpg.Pool] = None
neo4j_driver: Optional[AsyncGraphDatabase] = None
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
# Neo4j
# ============================================================================
async def init_neo4j():
    """Initialize Neo4j driver"""
    if not HAS_NEO4J or AsyncGraphDatabase is None:
        log.warning("Neo4j driver not available. Skipping Neo4j initialization.")
        return
    
    settings = _get_db_settings().database
    global neo4j_driver
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
            max_connection_lifetime=settings.neo4j_max_connection_lifetime,
            max_connection_pool_size=settings.neo4j_max_connection_pool_size,
            connection_acquisition_timeout=settings.neo4j_connection_timeout
        )
        # Test connection and apply schema
        async with neo4j_driver.session() as session:
            await session.run("RETURN 1")
            
            # Apply Graph Schema using Switchboard
            try:
                from mahoun.switchboard import switchboard
                import os
                
                schema_path = switchboard.get_schema("ingestion")
                if schema_path.endswith('.cypher') and os.path.exists(schema_path):
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        cypher_content = f.read()
                    
                    # Split by ';' and execute statements individually
                    statements = [s.strip() for s in cypher_content.split(';') if s.strip() and not s.strip().startswith('//')]
                    
                    for statement in statements:
                        try:
                            # Skip pure comments that might have slipped through
                            if not statement.startswith('//'):
                                await session.run(statement)
                        except Exception as st_err:
                            log.warning(f"Neo4j schema execution warning (might be safe to ignore): {st_err}")
                            
                    log.info(f"✅ Neo4j schema applied from {schema_path}")
            except Exception as e:
                log.warning(f"⚠️ Could not apply Neo4j schema automatically: {e}")
                
        log.info("✅ Neo4j driver initialized")
    except Exception as e:
        log.error(f"❌ Failed to initialize Neo4j driver: {e}")
        raise


async def close_neo4j():
    """Close Neo4j driver"""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        log.info("Neo4j driver closed")


async def get_neo4j():
    """Get Neo4j session"""
    if not HAS_NEO4J:
        raise RuntimeError("Neo4j driver not installed. Install with: pip install neo4j")
    if not neo4j_driver:
        await init_neo4j()
    if neo4j_driver:
        async with neo4j_driver.session() as session:
            yield session
    else:
        raise RuntimeError("Neo4j driver not initialized")


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
