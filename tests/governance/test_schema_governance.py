import pytest
from unittest.mock import MagicMock, patch
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError
from mahoun.graph.neo4j.schema import SchemaManager, Constraint
from mahoun.graph.neo4j.runner import GovernedSchemaRunner

@pytest.mark.asyncio
async def test_schema_governance_enforcement():
    # Mock the internal executor to avoid actually hitting Neo4j
    mock_session = MagicMock()

    # We need to ensure _execute_authorized returns something that looks like an empty list
    mock_session._execute_authorized.return_value = []

    # 1. Test authorized path (with active context)
    async with GovernanceContextManager.active_context(correlation_id="test-1", actor_id="admin"):
        runner = GovernedSchemaRunner(mock_session)
        manager = SchemaManager(runner)

        # This should succeed
        assert manager.create_constraint(Constraint("test_const", "Test", ["id"], "unique")) is True

    # 2. Test unauthorized path (no active context)
    # The requirement is that we must be inside GovernanceContext.
    # We reset the context stack to ensure it's empty
    GovernanceContextManager._reset_for_test()

    # The governance check happens in the runner's _execute_authorized path,
    # which goes through GovernedNeo4jSession. Since we're using a mock,
    # we need to make the mock's _execute_authorized raise when no context is active.
    def unauthorized_execute(query, params):
        GovernanceContextManager.require_context()
        return []

    mock_session._execute_authorized.side_effect = unauthorized_execute

    runner_unauthorized = GovernedSchemaRunner(mock_session)
    manager_unauthorized = SchemaManager(runner_unauthorized)

    # SchemaManager catches exceptions and returns False, but the
    # GovernanceViolationError is still raised by require_context().
    # Since SchemaManager.create_constraint has a broad except clause,
    # we verify the governance gate blocks the operation via return value.
    result = manager_unauthorized.create_constraint(Constraint("test_const2", "Test", ["id"], "unique"))
    assert result is False
