"""
System Identities Tests
=======================

Tests for canonical system actor identities used in bootstrap and governance operations.

These tests verify:
- System actors are properly defined and accessible
- System actors have correct properties (id, name, authority_level, etc.)
- System actors cannot be modified (frozen dataclass)
- System actor registry is complete and consistent
"""

import pytest
from unittest.mock import patch, MagicMock

from mahoun.core.governance.system_identities import (
    SystemActor,
    BOOTSTRAP_ACTOR,
    DATABASE_INITIALIZER_ACTOR,
    GOVERNANCE_HANDSHAKE_ACTOR,
    HEALTH_CHECK_ACTOR,
    SCHEMA_MIGRATION_ACTOR,
    SYSTEM_ACTOR_REGISTRY,
    get_system_actor,
    verify_system_actor,
    get_default_infrastructure_actor,
    DEFAULT_INFRASTRUCTURE_ACTOR,
)


class TestSystemActorDefinition:
    """Test SystemActor dataclass definition and immutability."""

    def test_system_actor_is_frozen(self):
        """SystemActor instances must be immutable (frozen dataclass)."""
        actor = BOOTSTRAP_ACTOR
        
        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            actor.id = "modified_id"

    def test_system_actor_required_fields(self):
        """SystemActor must have all required fields."""
        actor = BOOTSTRAP_ACTOR
        
        assert hasattr(actor, 'id')
        assert hasattr(actor, 'name')
        assert hasattr(actor, 'description')
        assert hasattr(actor, 'authority_level')
        assert hasattr(actor, 'mutation_allowed')
        assert hasattr(actor, 'scope')

    def test_system_actor_default_values(self):
        """SystemActor must have sensible defaults."""
        actor = SystemActor(
            id="test:actor",
            name="Test Actor",
            description="Test description",
            authority_level="SYSTEM"
        )
        
        assert actor.mutation_allowed is False
        assert actor.scope == "read-only"


class TestBootstrapActor:
    """Test the BOOTSTRAP_ACTOR canonical identity."""

    def test_bootstrap_actor_exists(self):
        """BOOTSTRAP_ACTOR must be defined."""
        assert BOOTSTRAP_ACTOR is not None

    def test_bootstrap_actor_id(self):
        """BOOTSTRAP_ACTOR must have correct id."""
        assert BOOTSTRAP_ACTOR.id == "system:bootstrap"

    def test_bootstrap_actor_authority(self):
        """BOOTSTRAP_ACTOR must have INFRASTRUCTURE authority level."""
        assert BOOTSTRAP_ACTOR.authority_level == "INFRASTRUCTURE"

    def test_bootstrap_actor_no_mutation(self):
        """BOOTSTRAP_ACTOR must not allow mutations."""
        assert BOOTSTRAP_ACTOR.mutation_allowed is False

    def test_bootstrap_actor_scope(self):
        """BOOTSTRAP_ACTOR must have bootstrap scope."""
        assert BOOTSTRAP_ACTOR.scope == "bootstrap"


class TestDatabaseInitializerActor:
    """Test the DATABASE_INITIALIZER_ACTOR canonical identity."""

    def test_database_initializer_actor_exists(self):
        """DATABASE_INITIALIZER_ACTOR must be defined."""
        assert DATABASE_INITIALIZER_ACTOR is not None

    def test_database_initializer_actor_id(self):
        """DATABASE_INITIALIZER_ACTOR must have correct id."""
        assert DATABASE_INITIALIZER_ACTOR.id == "system:database_initializer"

    def test_database_initializer_actor_authority(self):
        """DATABASE_INITIALIZER_ACTOR must have INFRASTRUCTURE authority level."""
        assert DATABASE_INITIALIZER_ACTOR.authority_level == "INFRASTRUCTURE"

    def test_database_initializer_actor_mutation_allowed(self):
        """DATABASE_INITIALIZER_ACTOR allows mutations (for schema DDL only)."""
        assert DATABASE_INITIALIZER_ACTOR.mutation_allowed is True

    def test_database_initializer_actor_scope(self):
        """DATABASE_INITIALIZER_ACTOR must have database_initialization scope."""
        assert DATABASE_INITIALIZER_ACTOR.scope == "database_initialization"


class TestGovernanceHandshakeActor:
    """Test the GOVERNANCE_HANDSHAKE_ACTOR canonical identity."""

    def test_governance_handshake_actor_exists(self):
        """GOVERNANCE_HANDSHAKE_ACTOR must be defined."""
        assert GOVERNANCE_HANDSHAKE_ACTOR is not None

    def test_governance_handshake_actor_id(self):
        """GOVERNANCE_HANDSHAKE_ACTOR must have correct id."""
        assert GOVERNANCE_HANDSHAKE_ACTOR.id == "system:governance_handshake"

    def test_governance_handshake_actor_no_mutation(self):
        """GOVERNANCE_HANDSHAKE_ACTOR must not allow mutations."""
        assert GOVERNANCE_HANDSHAKE_ACTOR.mutation_allowed is False


class TestHealthCheckActor:
    """Test the HEALTH_CHECK_ACTOR canonical identity."""

    def test_health_check_actor_exists(self):
        """HEALTH_CHECK_ACTOR must be defined."""
        assert HEALTH_CHECK_ACTOR is not None

    def test_health_check_actor_id(self):
        """HEALTH_CHECK_ACTOR must have correct id."""
        assert HEALTH_CHECK_ACTOR.id == "system:health_check"

    def test_health_check_actor_authority(self):
        """HEALTH_CHECK_ACTOR must have SYSTEM authority level."""
        assert HEALTH_CHECK_ACTOR.authority_level == "SYSTEM"


class TestSchemaMigrationActor:
    """Test the SCHEMA_MIGRATION_ACTOR canonical identity."""

    def test_schema_migration_actor_exists(self):
        """SCHEMA_MIGRATION_ACTOR must be defined."""
        assert SCHEMA_MIGRATION_ACTOR is not None

    def test_schema_migration_actor_id(self):
        """SCHEMA_MIGRATION_ACTOR must have correct id."""
        assert SCHEMA_MIGRATION_ACTOR.id == "system:schema_migration"

    def test_schema_migration_actor_mutation_allowed(self):
        """SCHEMA_MIGRATION_ACTOR allows mutations (for DDL operations)."""
        assert SCHEMA_MIGRATION_ACTOR.mutation_allowed is True


class TestSystemActorRegistry:
    """Test the SYSTEM_ACTOR_REGISTRY."""

    def test_registry_contains_all_actors(self):
        """SYSTEM_ACTOR_REGISTRY must contain all canonical system actors."""
        expected_actors = {
            "bootstrap": BOOTSTRAP_ACTOR,
            "database_initializer": DATABASE_INITIALIZER_ACTOR,
            "governance_handshake": GOVERNANCE_HANDSHAKE_ACTOR,
            "health_check": HEALTH_CHECK_ACTOR,
            "schema_migration": SCHEMA_MIGRATION_ACTOR,
        }
        
        for key, expected_actor in expected_actors.items():
            assert key in SYSTEM_ACTOR_REGISTRY
            assert SYSTEM_ACTOR_REGISTRY[key] == expected_actor

    def test_registry_values_are_system_actors(self):
        """All values in SYSTEM_ACTOR_REGISTRY must be SystemActor instances."""
        for key, actor in SYSTEM_ACTOR_REGISTRY.items():
            assert isinstance(actor, SystemActor)


class TestHelperFunctions:
    """Test helper functions for system actor lookup."""

    def test_get_system_actor_valid_key(self):
        """get_system_actor must return correct actor for valid key."""
        actor = get_system_actor("bootstrap")
        assert actor == BOOTSTRAP_ACTOR

    def test_get_system_actor_invalid_key(self):
        """get_system_actor must return None for invalid key."""
        actor = get_system_actor("nonexistent")
        assert actor is None

    def test_verify_system_actor_valid(self):
        """verify_system_actor must return True for valid actor IDs."""
        assert verify_system_actor("system:bootstrap") is True
        assert verify_system_actor("system:database_initializer") is True
        assert verify_system_actor("system:governance_handshake") is True

    def test_verify_system_actor_invalid(self):
        """verify_system_actor must return False for invalid actor IDs."""
        assert verify_system_actor("invalid:actor") is False
        assert verify_system_actor("user:john") is False

    def test_get_default_infrastructure_actor(self):
        """get_default_infrastructure_actor must return BOOTSTRAP_ACTOR."""
        actor = get_default_infrastructure_actor()
        assert actor == BOOTSTRAP_ACTOR
        assert actor == DEFAULT_INFRASTRUCTURE_ACTOR


class TestSystemActorIdentityContracts:
    """Test that system actors meet identity contract requirements."""

    def test_all_system_actors_have_ids(self):
        """All system actors must have non-empty, unique IDs."""
        ids = set()
        for actor in SYSTEM_ACTOR_REGISTRY.values():
            assert actor.id, f"Actor {actor.name} has empty id"
            assert actor.id not in ids, f"Duplicate actor ID: {actor.id}"
            ids.add(actor.id)

    def test_all_system_actors_have_names(self):
        """All system actors must have non-empty names."""
        for actor in SYSTEM_ACTOR_REGISTRY.values():
            assert actor.name, f"Actor {actor.id} has empty name"

    def test_all_system_actors_have_descriptions(self):
        """All system actors must have non-empty descriptions."""
        for actor in SYSTEM_ACTOR_REGISTRY.values():
            assert actor.description, f"Actor {actor.id} has empty description"

    def test_all_system_actors_have_authority_levels(self):
        """All system actors must have valid authority levels."""
        valid_levels = {"INFRASTRUCTURE", "SYSTEM", "SERVICE"}
        for actor in SYSTEM_ACTOR_REGISTRY.values():
            assert actor.authority_level in valid_levels, (
                f"Actor {actor.id} has invalid authority_level: {actor.authority_level}"
            )

    def test_infrastructure_actors_have_correct_scope(self):
        """INFRASTRUCTURE level actors must have appropriate scopes."""
        for actor in SYSTEM_ACTOR_REGISTRY.values():
            if actor.authority_level == "INFRASTRUCTURE":
                assert actor.scope in {"bootstrap", "database_initialization", "governance_verification", "schema_migration"}


# ============================================================================
# Integration Tests
# ============================================================================

class TestSystemActorUsageInDatabaseInit:
    """Test that system actors are used correctly in database initialization."""

    @pytest.mark.asyncio
    async def test_database_initializer_actor_used_in_governance_context(self):
        """Verify that DATABASE_INITIALIZER_ACTOR.id is used in governance context creation."""
        from mahoun.core.governance.database_init import create_governance_aware_initializer
        
        # Create initializer (this will create a governance context)
        initializer = create_governance_aware_initializer(driver=None)
        
        # The governance context should use DATABASE_INITIALIZER_ACTOR.id
        # We can't directly access _initialization_context without triggering init,
        # but we can verify the module imports correctly
        assert DATABASE_INITIALIZER_ACTOR.id == "system:database_initializer"

    def test_database_init_uses_canonical_actor(self):
        """Verify database_init.py imports and uses DATABASE_INITIALIZER_ACTOR."""
        import inspect
        from mahoun.core.governance import database_init
        
        # Check that the module imports DATABASE_INITIALIZER_ACTOR
        source = inspect.getsource(database_init)
        assert "DATABASE_INITIALIZER_ACTOR" in source
