import asyncio
from unittest.mock import MagicMock
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError
from mahoun.graph.neo4j.schema import SchemaManager, Constraint
from mahoun.graph.neo4j.runner import GovernedSchemaRunner

def test():
    GovernanceContextManager._reset_for_test()
    mock_session = MagicMock()
    
    def unauthorized_execute(query, params):
        print("MOCK CALLED")
        GovernanceContextManager.require_context()
        return []
        
    mock_session._execute_authorized.side_effect = unauthorized_execute
    runner_unauthorized = GovernedSchemaRunner(mock_session)
    manager_unauthorized = SchemaManager(runner_unauthorized)
    
    try:
        result = manager_unauthorized.create_constraint(Constraint("test_const2", "Test", ["id"], "unique"))
        print(f"Result: {result}")
        print(f"Called: {mock_session._execute_authorized.called}")
    except Exception as e:
        print(f"Exception: {e}")

test()
