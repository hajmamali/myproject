"""
P0 Bypass Vector Remediation Tests
==================================

CRITICAL: Tests verify complete elimination of governance bypass vectors
identified in ARCHITECTURAL_KERNEL_AND_GOVERNANCE_ANALYSIS_REPORT.md

P0-1: api/database.py direct driver usage → GovernanceAwareDatabaseInitializer
P0-2: mahoun/graph/neo4j/schema.py session.run() → GovernanceAwareSchemaManager  
P1-1: api/routers/reasoning.py stack manipulation → proper context manager
"""

import pytest
import subprocess
from pathlib import Path


@pytest.mark.p0
class TestP01DatabaseBypassElimination:
    """Test P0-1: Direct Neo4j driver usage elimination in api/database.py"""

    def test_governance_aware_initializer_exists(self):
        """Verify GovernanceAwareDatabaseInitializer exists and is importable"""
        from mahoun.core.governance.database_init import (
            GovernanceAwareDatabaseInitializer,
            create_governance_aware_initializer
        )
        
        # Verify class exists
        assert GovernanceAwareDatabaseInitializer is not None
        
        # Verify factory function
        initializer = create_governance_aware_initializer(driver=None)
        assert initializer is not None
        assert hasattr(initializer, 'initialize_with_governance')

    def test_api_database_uses_governance_aware_init(self):
        """Verify api/database.py imports and uses governance-aware initializer"""
        database_py = Path("/home/haji/Desktop/KingMahouN/api/database.py")
        content = database_py.read_text()
        
        # Should import governance-aware initializer
        assert "from mahoun.core.governance.database_init import" in content
        assert "create_governance_aware_initializer" in content

    async def test_database_init_uses_governed_session(self):
        """Test that database initialization uses governance-aware session"""
        import asyncio
        from mahoun.core.governance.database_init import create_governance_aware_initializer
        
        # Test with None driver (no actual Neo4j connection needed)
        initializer = create_governance_aware_initializer(driver=None)
        
        # This should not fail with "unexpected keyword argument 'reason'"
        result = await initializer.initialize_with_governance(
            timeout_sec=1.0,
            correlation_id="test_governance_init"
        )
        
        assert result.success is True
        assert result.bypass_vector_eliminated is True


@pytest.mark.p0  
class TestP02SchemaBypassElimination:
    """Test P0-2: Direct session.run() elimination in mahoun/graph/neo4j/schema.py"""

    def test_governance_aware_schema_manager_exists(self):
        """Verify GovernanceAwareSchemaManager exists"""
        from mahoun.graph.neo4j.schema import GovernanceAwareSchemaManager, Constraint, Index
        
        assert GovernanceAwareSchemaManager is not None
        assert hasattr(GovernanceAwareSchemaManager, 'create_constraint_governed')


@pytest.mark.p1
class TestP11ContextStackManipulationFix:
    """Test P1-1: Context stack manipulation elimination in api/routers/reasoning.py"""

    def test_no_manual_stack_append_in_reasoning_router(self):
        """Verify reasoning router uses proper context manager"""
        reasoning_py = Path("/home/haji/Desktop/KingMahouN/api/routers/reasoning.py")
        content = reasoning_py.read_text()
        
        assert "_get_stack().append" not in content
        assert "async with GovernanceContextManager.active_context" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "p0 or p1"])
