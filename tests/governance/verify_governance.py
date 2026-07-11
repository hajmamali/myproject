import asyncio
from unittest.mock import MagicMock
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError
from mahoun.graph.neo4j.schema import SchemaManager, Constraint
from mahoun.graph.neo4j.runner import GovernedSchemaRunner

async def main():
    print("Starting governance verification...")
    # Mock the internal executor to avoid actually hitting Neo4j
    mock_session = MagicMock()
    mock_session._execute_authorized.return_value = []

    # 1. Test authorized path (with active context)
    print("Testing authorized path...")
    async with GovernanceContextManager.active_context(correlation_id="test-1", actor_id="admin"):
        runner = GovernedSchemaRunner(mock_session)
        manager = SchemaManager(runner)
        
        # This should succeed
        assert manager.create_constraint(Constraint("test_const", "Test", ["id"], "unique")) is True
    print("✅ Authorized path succeeded.")
        
    # 2. Test unauthorized path (no active context)
    print("Testing unauthorized path...")
    # Reset context
    GovernanceContextManager._reset_for_test()
    
    runner_unauthorized = GovernedSchemaRunner(mock_session)
    manager_unauthorized = SchemaManager(runner_unauthorized)
    
    try:
        # This should raise GovernanceViolationError because no context is active
        manager_unauthorized.create_constraint(Constraint("test_const", "Test", ["id"], "unique"))
        print("❌ FAILED: Should have raised GovernanceViolationError")
    except GovernanceViolationError:
        print("✅ Correct: GovernanceViolationError raised.")
    except Exception as e:
        print(f"❌ FAILED: Raised unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
