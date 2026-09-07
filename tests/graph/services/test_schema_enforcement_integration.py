"""
Schema Enforcement Integration Tests
=====================================

These tests prove that SchemaManager.enforce_schema_or_die() raises
ConstitutionalSchemaViolation when required constraints/indexes are missing.

Run: ``pytest tests/graph/services/test_schema_enforcement_integration.py -v``
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from mahoun.graph.neo4j.schema import (
    ConstitutionalSchemaViolation,
    GovernanceAwareSchemaManager,
    SchemaManager,
)
from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection


SYSTEM_ACTOR = "system:database_initializer"


@pytest_asyncio.fixture
async def schema_connection() -> Neo4jConnection:
    """Live Neo4j connection. Fails loudly if unreachable."""
    try:
        conn = get_connection()
        conn.execute_query("RETURN 1 AS n")
        return conn
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"Schema enforcement integration tests require a live Neo4j. "
            f"Connection failed: {exc!r}"
        )


@pytest_asyncio.fixture
async def schema_manager(schema_connection: Neo4jConnection):
    """GovernedSchemaManager instance for testing enforce_schema_or_die."""
    return GovernanceAwareSchemaManager(schema_connection._driver)


class TestSchemaValidation:
    """Test that validate_schema correctly identifies missing constraints."""

    async def test_validate_schema_returns_dict(
        self, schema_connection: Neo4jConnection
    ) -> None:
        """validate_schema returns a dict with constraints, indexes, fulltext_indexes keys."""
        manager = SchemaManager(schema_connection)
        results = manager.validate_schema()

        assert isinstance(results, dict)
        assert set(results.keys()) == {"constraints", "indexes", "fulltext_indexes"}
        assert all(isinstance(v, bool) for v in results.values())


class TestEnforceSchemaOrDie:
    """Test that enforce_schema_or_die raises on missing requirements."""

    async def test_enforce_schema_or_die_raises_on_missing_constraints(
        self, schema_manager: GovernanceAwareSchemaManager, schema_connection: Neo4jConnection
    ) -> None:
        """If a required constraint is missing, enforce_schema_or_die raises ConstitutionalSchemaViolation.

        This test temporarily drops a known required constraint, calls enforce_schema_or_die,
        and verifies the exception is raised. Then restores the constraint.
        """
        # First, verify the constraint exists
        manager = SchemaManager(schema_connection)
        constraints_before = manager.get_constraints()
        constraint_names = {c.get("name") for c in constraints_before}

        # Use a constraint we know exists from the canonical set
        required_constraint = "unique_norm_id"
        assert required_constraint in constraint_names, (
            f"Test setup failed: {required_constraint} should exist before test"
        )

        # Drop the constraint
        dropped = manager.drop_constraint(required_constraint)
        assert dropped is True, "Failed to drop constraint for test"

        try:
            # Now enforce_schema_or_die should raise
            with pytest.raises(ConstitutionalSchemaViolation) as exc_info:
                manager.enforce_schema_or_die()

            assert "constraints" in str(exc_info.value).lower()
            assert required_constraint in str(exc_info.value)
        finally:
            # Restore the constraint (re-run the canonical schema creation)
            from mahoun.graph.neo4j.create_new_constraints import main as create_constraints_main
            await create_constraints_main()

    async def test_enforce_schema_or_die_raises_on_missing_index(
        self, schema_manager: GovernanceAwareSchemaManager, schema_connection: Neo4jConnection
    ) -> None:
        """If a required index is missing, enforce_schema_or_die raises ConstitutionalSchemaViolation."""
        manager = SchemaManager(schema_connection)
        indexes_before = manager.get_indexes()
        index_names = {i.get("name") for i in indexes_before}

        # Use an index we know exists
        required_index = "law_name_idx"
        assert required_index in index_names, (
            f"Test setup failed: {required_index} should exist before test"
        )

        dropped = manager.drop_index(required_index)
        assert dropped is True, "Failed to drop index for test"

        try:
            with pytest.raises(ConstitutionalSchemaViolation) as exc_info:
                manager.enforce_schema_or_die()

            assert "indexes" in str(exc_info.value).lower()
            assert required_index in str(exc_info.value)
        finally:
            # Restore by re-creating indexes
            manager.create_indexes()

    async def test_enforce_schema_or_die_raises_on_missing_fulltext(
        self, schema_manager: GovernanceAwareSchemaManager, schema_connection: Neo4jConnection
    ) -> None:
        """If a required fulltext index is missing, enforce_schema_or_die raises ConstitutionalSchemaViolation."""
        manager = SchemaManager(schema_connection)
        indexes_before = manager.get_indexes()
        index_names = {i.get("name") for i in indexes_before}

        required_fulltext = "law_fulltext_idx"
        assert required_fulltext in index_names, (
            f"Test setup failed: {required_fulltext} should exist before test"
        )

        dropped = manager.drop_index(required_fulltext)
        assert dropped is True, "Failed to drop fulltext index for test"

        try:
            with pytest.raises(ConstitutionalSchemaViolation) as exc_info:
                manager.enforce_schema_or_die()

            assert "fulltext_indexes" in str(exc_info.value).lower()
            assert required_fulltext in str(exc_info.value)
        finally:
            manager.create_fulltext_indexes()


class TestGovernanceAwareSchemaManager:
    """Test that GovernanceAwareSchemaManager routes through governance boundary."""

    async def test_create_constraint_governed_works(
        self, schema_manager: GovernanceAwareSchemaManager
    ) -> None:
        """create_constraint_governed executes through governed session."""
        from mahoun.graph.neo4j.schema import Constraint

        test_constraint = Constraint(
            name="test_schema_enforcement_dummy",
            label="Law",
            properties=["test_prop"],
            constraint_type="unique",
        )

        result = await schema_manager.create_constraint_governed(test_constraint)
        # Should succeed (or fail if already exists)
        assert isinstance(result, bool)

        # Clean up - drop the test constraint
        from mahoun.graph.neo4j.connection import get_connection
        conn = get_connection()
        mgr = SchemaManager(conn)
        mgr.drop_constraint("test_schema_enforcement_dummy")

    async def test_create_index_governed_works(
        self, schema_manager: GovernanceAwareSchemaManager
    ) -> None:
        """create_index_governed executes through governed session."""
        from mahoun.graph.neo4j.schema import Index

        test_index = Index(
            name="test_schema_enforcement_idx",
            label="Law",
            properties=["test_prop"],
            index_type="btree",
        )

        result = await schema_manager.create_index_governed(test_index)
        assert isinstance(result, bool)

        # Clean up
        from mahoun.graph.neo4j.connection import get_connection
        conn = get_connection()
        mgr = SchemaManager(conn)
        mgr.drop_index("test_schema_enforcement_idx")

    async def test_get_constraints_governed_returns_list(
        self, schema_manager: GovernanceAwareSchemaManager
    ) -> None:
        """get_constraints_governed returns list of constraint dicts."""
        constraints = await schema_manager.get_constraints_governed()
        assert isinstance(constraints, list)
        assert all(isinstance(c, dict) for c in constraints)
        assert all("name" in c for c in constraints)

    async def test_get_indexes_governed_returns_list(
        self, schema_manager: GovernanceAwareSchemaManager
    ) -> None:
        """get_indexes_governed returns list of index dicts."""
        indexes = await schema_manager.get_indexes_governed()
        assert isinstance(indexes, list)
        assert all(isinstance(i, dict) for i in indexes)
        assert all("name" in i for i in indexes)


class TestConstitutionalSchemaViolation:
    """Test the ConstitutionalSchemaViolation exception."""

    def test_exception_is_runtime_error(self) -> None:
        """ConstitutionalSchemaViolation is a RuntimeError."""
        exc = ConstitutionalSchemaViolation("test message")
        assert isinstance(exc, RuntimeError)

    def test_exception_message_preserved(self) -> None:
        """Exception message is preserved."""
        msg = "Custom constitutional violation message"
        exc = ConstitutionalSchemaViolation(msg)
        assert str(exc) == msg


class TestSchemaManagerRequiresGovernedRunner:
    """Test that SchemaManager rejects raw Neo4j sessions."""

    def test_raw_session_rejected(self) -> None:
        """Passing a raw neo4j.Session raises TypeError."""
        from unittest.mock import MagicMock
        from neo4j import Session

        mock_session = MagicMock(spec=Session)
        with pytest.raises(TypeError) as exc_info:
            SchemaManager(mock_session)
        assert "GovernedSchemaRunner" in str(exc_info.value)
        assert "raw Neo4j sessions are not an authorized schema execution surface" in str(exc_info.value)