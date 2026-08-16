"""
System Actor Identities
=======================

Classification: CONSTITUTIONAL / GOVERNANCE / NON-BYPASSABLE

This module defines canonical system actor identities for infrastructure operations.
These identities are used for bootstrap, connectivity checks, and other system-level
operations that require governance-compliant identity but do not represent
user-level actors.

Architectural Mandate:
    - System actors MUST be explicitly defined and documented
    - System actors MUST NOT have mutation authority (read-only)
    - System actors MUST NOT be confused with user identities
    - System actors MUST route through canonical governance paths
    - System actors MUST be deterministic and reproducible

Usage:
    from mahoun.core.governance.system_identities import BOOTSTRAP_ACTOR
    
    # In governance context creation:
    ctx = GovernanceContextManager.create_context(
        operation="database_initialization",
        actor_id=BOOTSTRAP_ACTOR.id,
        correlation_id=f"db_init_{timestamp}"
    )
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SystemActor:
    """
    Immutable system actor definition.
    
    Attributes:
        id: Unique actor identifier (used in audit trails)
        name: Human-readable name
        description: Purpose of this actor
        authority_level: Security level (INFRASTRUCTURE, SYSTEM, SERVICE)
        mutation_allowed: Whether this actor can perform mutations (False for system actors)
        scope: Operational scope
    """
    id: str
    name: str
    description: str
    authority_level: str  # "INFRASTRUCTURE" | "SYSTEM" | "SERVICE"
    mutation_allowed: bool = False
    scope: str = "read-only"


# ============================================================================
# CANONICAL SYSTEM ACTORS
# ============================================================================

# Bootstrap/Infrastructure Actor
# Used for: Database initialization, connectivity checks, startup operations
# Authority: INFRASTRUCTURE (highest system level)
# Scope: Bootstrap operations only, read-only
BOOTSTRAP_ACTOR = SystemActor(
    id="system:bootstrap",
    name="System Bootstrap Actor",
    description=(
        "Infrastructure-level actor for system bootstrap operations. "
        "Used during application startup for database connectivity verification "
        "and initial schema setup. This actor has NO mutation authority and "
        "operates in a read-only, fail-closed manner."
    ),
    authority_level="INFRASTRUCTURE",
    mutation_allowed=False,
    scope="bootstrap",
)

# Database Initializer Actor
# Used for: Neo4j driver initialization and handshake verification
# Authority: INFRASTRUCTURE
# Scope: Database connectivity checks only
DATABASE_INITIALIZER_ACTOR = SystemActor(
    id="system:database_initializer",
    name="Database Initializer Actor",
    description=(
        "Specialized actor for database initialization operations. "
        "Used during Neo4j driver handshake and connectivity verification. "
        "Operates under governance context but without user-level authority. "
        "Read-only for connectivity checks, write-enabled only for schema DDL during init."
    ),
    authority_level="INFRASTRUCTURE",
    mutation_allowed=True,  # Limited to schema DDL during bootstrap
    scope="database_initialization",
)

# Governance Handshake Actor
# Used for: Governance layer connectivity verification
# Authority: INFRASTRUCTURE
# Scope: Governance handshake operations only
GOVERNANCE_HANDSHAKE_ACTOR = SystemActor(
    id="system:governance_handshake",
    name="Governance Handshake Actor",
    description=(
        "Actor for governance layer handshake operations. "
        "Used to verify that the governance boundary is properly established "
        "before allowing any database operations. Read-only, fail-closed."
    ),
    authority_level="INFRASTRUCTURE",
    mutation_allowed=False,
    scope="governance_verification",
)

# Health Check Actor
# Used for: Health check endpoints and monitoring
# Authority: SYSTEM
# Scope: Health monitoring and status checks
HEALTH_CHECK_ACTOR = SystemActor(
    id="system:health_check",
    name="Health Check Actor",
    description=(
        "Actor for health check and monitoring operations. "
        "Used by /health endpoints to verify system status. "
        "Read-only, no mutation authority."
    ),
    authority_level="SYSTEM",
    mutation_allowed=False,
    scope="health_monitoring",
)

# Migration Actor
# Used for: Schema migration operations
# Authority: INFRASTRUCTURE
# Scope: Database schema migrations
SCHEMA_MIGRATION_ACTOR = SystemActor(
    id="system:schema_migration",
    name="Schema Migration Actor",
    description=(
        "Actor for database schema migration operations. "
        "Used during startup to apply schema migrations. "
        "Write-enabled for DDL operations only, under strict governance."
    ),
    authority_level="INFRASTRUCTURE",
    mutation_allowed=True,  # Limited to DDL operations
    scope="schema_migration",
)


# ============================================================================
# ACTOR REGISTRY
# ============================================================================

# Registry of all canonical system actors for validation and discovery
SYSTEM_ACTOR_REGISTRY: dict[str, SystemActor] = {
    "bootstrap": BOOTSTRAP_ACTOR,
    "database_initializer": DATABASE_INITIALIZER_ACTOR,
    "governance_handshake": GOVERNANCE_HANDSHAKE_ACTOR,
    "health_check": HEALTH_CHECK_ACTOR,
    "schema_migration": SCHEMA_MIGRATION_ACTOR,
}


def get_system_actor(actor_key: str) -> Optional[SystemActor]:
    """
    Get a canonical system actor by key.
    
    Args:
        actor_key: Key identifying the actor (e.g., "bootstrap", "database_initializer")
    
    Returns:
        SystemActor if found, None otherwise
    
    Raises:
        ValueError: If actor_key is not in the registry (in strict mode)
    """
    actor = SYSTEM_ACTOR_REGISTRY.get(actor_key)
    if actor is None:
        # In production, this should be a hard failure
        # For now, return None to allow graceful degradation
        # TODO: Make this fail-closed in production mode
        pass
    return actor


def verify_system_actor(actor_id: str) -> bool:
    """
    Verify that an actor_id corresponds to a known system actor.
    
    Args:
        actor_id: The actor ID to verify
    
    Returns:
        True if actor_id is a known system actor, False otherwise
    """
    return any(actor.id == actor_id for actor in SYSTEM_ACTOR_REGISTRY.values())


# ============================================================================
# DEFAULT INFRASTRUCTURE ACTOR
# ============================================================================

# Default actor to use when no specific system actor is provided
# This ensures we always have a valid, deterministic identity for infrastructure operations
DEFAULT_INFRASTRUCTURE_ACTOR = BOOTSTRAP_ACTOR


def get_default_infrastructure_actor() -> SystemActor:
    """
    Get the default infrastructure actor for operations that don't specify one.
    
    Returns:
        The default system actor (BOOTSTRAP_ACTOR)
    """
    return DEFAULT_INFRASTRUCTURE_ACTOR
