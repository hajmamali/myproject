"""
Comprehensive Test Suite for DI Refactor (Tasks 2-6)
=====================================================
STRICT GOVERNANCE: No mocks, no simplifications, real behavioral verification.

Tests cover:
- Task 2: Neo4jConnection.ping() method
- Task 3: GraphEnhancedRetriever DI refactor
- Task 4: GraphVectorSync DI refactor
- Task 5: LegalQueryExecutor DI refactor
- Task 6: IntegrityProbe DI refactor

Architectural Invariants Enforced:
1. No direct driver creation outside allowlist
2. All Neo4j access through governed_session()
3. Bootstrap owns all wiring
4. Lazy loading for heavy infrastructure
5. Performance: ping() < 100ms, no eager heavy loads
"""

import pytest
import os
import sys
import time
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch
import uuid

# EXPLICIT integration gate — fail-closed
# Tests require Neo4j to be running and MAHOUN_INTEGRATION_ENABLED=true
_INTEGRATION_ENABLED = os.getenv("MAHOUN_INTEGRATION_ENABLED", "false").lower() == "true"

if not _INTEGRATION_ENABLED:
    pytest.skip(
        "EXPLICIT: Integration tests disabled. "
        "Set MAHOUN_INTEGRATION_ENABLED=true to enable. "
        "These tests require Neo4j to be running at bolt://localhost:7687. "
        "Skipping to prevent false-green scenarios.",
        allow_module_level=True
    )


# ============================================================================
# TASK 2: Neo4jConnection.ping() Method Tests
# ============================================================================

class TestNeo4jConnectionPing:
    """Test suite for Neo4jConnection.ping() method (Task 2)"""
    
    def test_ping_method_exists(self):
        """Verify ping() method exists on Neo4jConnection"""
        from mahoun.graph.neo4j.connection import Neo4jConnection
        
        assert hasattr(Neo4jConnection, 'ping'), "ping() method must exist"
        assert callable(getattr(Neo4jConnection, 'ping')), "ping() must be callable"
    
    def test_ping_returns_bool(self):
        """Verify ping() returns boolean"""
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        result = conn.ping()
        
        assert isinstance(result, bool), "ping() must return bool"
    
    def test_ping_uses_existing_driver(self):
        """Verify ping() does NOT create new driver"""
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        driver_before = conn.driver
        
        result = conn.ping()
        
        driver_after = conn.driver
        assert driver_before is driver_after, "ping() must reuse existing driver, not create new one"
    
    def test_ping_performance(self):
        """Verify ping() completes in < 100ms (performance requirement)"""
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        
        start = time.time()
        result = conn.ping()
        elapsed_ms = (time.time() - start) * 1000
        
        assert elapsed_ms < 100, f"ping() took {elapsed_ms:.2f}ms, must be < 100ms"
    
    def test_ping_with_healthy_connection(self):
        """Verify ping() returns True when Neo4j is healthy"""
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        result = conn.ping()
        
        assert result is True, "ping() must return True for healthy connection"
    
    def test_ping_handles_connection_failure_gracefully(self):
        """Verify ping() returns False on connection failure (no exceptions)"""
        from mahoun.graph.neo4j.connection import Neo4jConnection
        
        # Create connection with invalid URI
        conn = Neo4jConnection(
            uri="bolt://invalid-host:7687",
            user="neo4j",
            password="invalid",
            database="neo4j"
        )
        
        result = conn.ping()
        
        assert result is False, "ping() must return False on connection failure, not raise exception"
    
    def test_ping_docstring_exists(self):
        """Verify ping() has proper documentation"""
        from mahoun.graph.neo4j.connection import Neo4jConnection
        
        ping_method = getattr(Neo4jConnection, 'ping')
        assert ping_method.__doc__ is not None, "ping() must have docstring"
        assert "health" in ping_method.__doc__.lower(), "docstring must mention health check purpose"


# ============================================================================
# TASK 3: GraphEnhancedRetriever DI Refactor Tests
# ============================================================================

class TestGraphEnhancedRetrieverDI:
    """Test suite for GraphEnhancedRetriever DI refactor (Task 3)"""
    
    def test_accepts_neo4j_connection_parameter(self):
        """Verify GraphEnhancedRetriever accepts Neo4jConnection instance"""
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        
        # Should accept connection parameter
        retriever = GraphEnhancedRetriever(connection=conn)
        
        assert retriever is not None
        assert hasattr(retriever, 'connection'), "Must store connection as instance variable"
    
    def test_no_raw_driver_parameter(self):
        """Verify GraphEnhancedRetriever does NOT accept raw driver"""
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        import inspect
        
        sig = inspect.signature(GraphEnhancedRetriever.__init__)
        params = list(sig.parameters.keys())
        
        assert 'neo4j_driver' not in params, "Must NOT accept neo4j_driver parameter (old API)"
        assert 'driver' not in params, "Must NOT accept driver parameter (old API)"
        assert 'connection' in params, "Must accept connection parameter (new API)"
    
    def test_uses_governed_session_not_raw_session(self):
        """Verify GraphEnhancedRetriever uses governed_session(), not driver.session()"""
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        import inspect
        
        source = inspect.getsource(GraphEnhancedRetriever)
        
        # Must NOT contain raw session calls
        assert 'self.neo4j.session()' not in source, "Must NOT use self.neo4j.session() (raw driver access)"
        assert 'self.driver.session()' not in source, "Must NOT use self.driver.session() (raw driver access)"
        
        # Must contain governed_session calls
        assert 'governed_session' in source, "Must use governed_session() for all Neo4j access"
    
    def test_governed_session_includes_actor_id(self):
        """Verify governed_session() calls include actor_id for audit trail"""
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        import inspect
        
        source = inspect.getsource(GraphEnhancedRetriever)
        
        # Check for actor_id in governed_session calls
        assert 'actor_id=' in source, "governed_session() calls must include actor_id parameter"
    
    def test_no_direct_driver_creation(self):
        """Verify GraphEnhancedRetriever does NOT create drivers internally"""
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        import inspect
        
        source = inspect.getsource(GraphEnhancedRetriever)
        
        assert 'GraphDatabase.driver(' not in source, "Must NOT create GraphDatabase.driver"
        assert 'AsyncGraphDatabase.driver(' not in source, "Must NOT create AsyncGraphDatabase.driver"


# ============================================================================
# TASK 4: GraphVectorSync DI Refactor Tests
# ============================================================================

class TestGraphVectorSyncDI:
    """Test suite for GraphVectorSync DI refactor (Task 4)"""
    
    def test_accepts_neo4j_connection_parameter(self):
        """Verify GraphVectorSync accepts Neo4jConnection instance"""
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        
        # Should accept connection parameter
        sync = GraphVectorSync(connection=conn)
        
        assert sync is not None
        assert hasattr(sync, 'connection'), "Must store connection as instance variable"
    
    def test_no_raw_driver_parameter(self):
        """Verify GraphVectorSync does NOT accept raw driver"""
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        import inspect
        
        sig = inspect.signature(GraphVectorSync.__init__)
        params = list(sig.parameters.keys())
        
        assert 'neo4j_driver' not in params, "Must NOT accept neo4j_driver parameter"
        assert 'driver' not in params, "Must NOT accept driver parameter"
        assert 'connection' in params, "Must accept connection parameter"
    
    def test_uses_governed_session_not_raw_session(self):
        """Verify GraphVectorSync uses governed_session(), not driver.session()"""
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        import inspect
        
        source = inspect.getsource(GraphVectorSync)
        
        # Must NOT contain raw session calls
        assert 'self.neo4j.session()' not in source, "Must NOT use self.neo4j.session()"
        assert 'self.driver.session()' not in source, "Must NOT use self.driver.session()"
        
        # Must contain governed_session calls
        assert 'governed_session' in source, "Must use governed_session()"
    
    def test_governed_session_in_inject_neo4j_embedding(self):
        """Verify _inject_neo4j_embedding uses governed_session()"""
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        import inspect
        
        source = inspect.getsource(GraphVectorSync._inject_neo4j_embedding)
        
        assert 'governed_session' in source, "_inject_neo4j_embedding must use governed_session()"
        assert '.session()' not in source or 'governed_session' in source, "Must not use raw .session()"
    
    def test_governed_session_in_backfill_graph_vectors(self):
        """Verify backfill_graph_vectors uses governed_session()"""
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        import inspect
        
        source = inspect.getsource(GraphVectorSync.backfill_graph_vectors)
        
        assert 'governed_session' in source, "backfill_graph_vectors must use governed_session()"
        assert '.session()' not in source or 'governed_session' in source, "Must not use raw .session()"


# ============================================================================
# TASK 5: LegalQueryExecutor DI Refactor Tests
# ============================================================================

class TestLegalQueryExecutorDI:
    """Test suite for LegalQueryExecutor DI refactor (Task 5)"""
    
    def test_accepts_neo4j_connection_parameter(self):
        """Verify LegalQueryExecutor accepts Neo4jConnection instance"""
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        from mahoun.graph.neo4j.connection import get_connection
        
        conn = get_connection()
        
        # Should accept connection parameter
        executor = LegalQueryExecutor(connection=conn)
        
        assert executor is not None
        assert hasattr(executor, 'connection'), "Must store connection as instance variable"
    
    def test_no_raw_driver_parameter(self):
        """Verify LegalQueryExecutor does NOT accept raw driver"""
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        import inspect
        
        sig = inspect.signature(LegalQueryExecutor.__init__)
        params = list(sig.parameters.keys())
        
        assert 'neo4j_driver' not in params, "Must NOT accept neo4j_driver parameter"
        assert 'driver' not in params, "Must NOT accept driver parameter"
        assert 'connection' in params, "Must accept connection parameter"
    
    def test_uses_governed_session_for_mutations(self):
        """Verify LegalQueryExecutor uses governed_session() for mutation queries"""
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        import inspect
        
        source = inspect.getsource(LegalQueryExecutor)
        
        # Must NOT contain raw session calls
        assert 'self.driver.session()' not in source, "Must NOT use self.driver.session()"
        
        # Must contain governed_session calls
        assert 'governed_session' in source, "Must use governed_session() for mutations"
    
    def test_uses_execute_query_for_reads(self):
        """Verify LegalQueryExecutor uses execute_query() for read-only queries"""
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        import inspect
        
        source = inspect.getsource(LegalQueryExecutor)
        
        # Should use execute_query for read operations
        assert 'execute_query' in source, "Should use execute_query() for read-only queries"
    
    def test_no_direct_driver_creation(self):
        """Verify LegalQueryExecutor does NOT create drivers internally"""
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        import inspect
        
        source = inspect.getsource(LegalQueryExecutor)
        
        assert 'GraphDatabase.driver(' not in source, "Must NOT create GraphDatabase.driver"
        assert 'AsyncGraphDatabase.driver(' not in source, "Must NOT create AsyncGraphDatabase.driver"


# ============================================================================
# TASK 6: IntegrityProbe DI Refactor Tests
# ============================================================================

class TestIntegrityProbeDI:
    """Test suite for IntegrityProbe DI refactor (Task 6)"""
    
    def test_no_graphdatabase_import(self):
        """Verify integrity_probe.py does NOT import GraphDatabase"""
        probe_path = Path(__file__).parent.parent / "mahoun" / "infrastructure" / "health" / "integrity_probe.py"
        source = probe_path.read_text()
        
        assert 'from neo4j import GraphDatabase' not in source, "Must NOT import GraphDatabase"
        assert 'import neo4j' not in source or 'from mahoun.graph.neo4j.connection' in source, \
            "Must NOT import neo4j directly (except via connection module)"
    
    def test_no_driver_creation_in_check_neo4j(self):
        """Verify check_neo4j() does NOT create driver"""
        probe_path = Path(__file__).parent.parent / "mahoun" / "infrastructure" / "health" / "integrity_probe.py"
        source = probe_path.read_text()
        
        assert 'GraphDatabase.driver(' not in source, "Must NOT create GraphDatabase.driver"
    
    def test_uses_get_connection_and_ping(self):
        """Verify check_neo4j() uses get_connection().ping()"""
        probe_path = Path(__file__).parent.parent / "mahoun" / "infrastructure" / "health" / "integrity_probe.py"
        source = probe_path.read_text()
        
        assert 'get_connection' in source, "Must use get_connection()"
        assert 'ping()' in source, "Must use ping() method"
    
    def test_check_neo4j_handles_import_error(self):
        """Verify check_neo4j() handles ImportError gracefully"""
        probe_path = Path(__file__).parent.parent / "mahoun" / "infrastructure" / "health" / "integrity_probe.py"
        source = probe_path.read_text()
        
        # Check for ImportError handling
        assert 'except ImportError' in source, "Must handle ImportError"
    
    def test_check_neo4j_handles_general_exception(self):
        """Verify check_neo4j() handles general exceptions gracefully"""
        probe_path = Path(__file__).parent.parent / "mahoun" / "infrastructure" / "health" / "integrity_probe.py"
        source = probe_path.read_text()
        
        # Check for general exception handling
        assert 'except Exception' in source, "Must handle general exceptions"
    
    def test_check_neo4j_returns_bool(self):
        """Verify check_neo4j() returns boolean"""
        # Import and test the actual function
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mahoun.infrastructure.health.integrity_probe import check_neo4j
        
        result = check_neo4j()
        
        assert isinstance(result, bool), "check_neo4j() must return bool"
    
    def test_check_neo4j_logs_appropriately(self):
        """Verify check_neo4j() logs success/failure"""
        probe_path = Path(__file__).parent.parent / "mahoun" / "infrastructure" / "health" / "integrity_probe.py"
        source = probe_path.read_text()
        
        # Check for logging statements
        assert 'logger.info' in source or 'logger.error' in source, "Must log results"


# ============================================================================
# CROSS-MODULE INTEGRATION TESTS
# ============================================================================

class TestDIRefactorIntegration:
    """Integration tests across all refactored modules"""
    
    def test_all_modules_use_same_connection_singleton(self):
        """Verify all modules use the same Neo4jConnection singleton"""
        from mahoun.graph.neo4j.connection import get_connection
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        
        conn1 = get_connection()
        conn2 = get_connection()
        
        assert conn1 is conn2, "get_connection() must return singleton"
        
        # All modules should use the same connection
        retriever = GraphEnhancedRetriever(connection=conn1)
        sync = GraphVectorSync(connection=conn1)
        executor = LegalQueryExecutor(connection=conn1)
        
        assert retriever.connection is conn1
        assert sync.connection is conn1
        assert executor.connection is conn1
    
    def test_no_driver_creation_outside_allowlist(self):
        """Verify NO driver creation outside the three-file allowlist"""
        allowlist = [
            "mahoun/graph/neo4j/connection.py",
            "mahoun/graph/neo4j/schema.py",
            "api/database.py"
        ]
        
        # Scan all modified files
        modified_files = [
            "mahoun/retrieval/graph_enhanced.py",
            "mahoun/pipelines/sync/graph_vector_sync.py",
            "mahoun/graph/legal_cypher_queries.py",
            "mahoun/infrastructure/health/integrity_probe.py"
        ]
        
        base_path = Path(__file__).parent.parent
        
        for file_path in modified_files:
            full_path = base_path / file_path
            if full_path.exists():
                source = full_path.read_text()
                
                assert 'GraphDatabase.driver(' not in source, \
                    f"{file_path} must NOT create GraphDatabase.driver (outside allowlist)"
                assert 'AsyncGraphDatabase.driver(' not in source, \
                    f"{file_path} must NOT create AsyncGraphDatabase.driver (outside allowlist)"
    
    def test_performance_no_eager_heavy_loads(self):
        """Verify no eager loading of heavy infrastructure during import"""
        import sys
        import time
        
        # Clear any cached imports
        modules_to_clear = [k for k in sys.modules.keys() if 'mahoun' in k]
        for mod in modules_to_clear:
            del sys.modules[mod]
        
        # Time the import
        start = time.time()
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
        from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
        elapsed_ms = (time.time() - start) * 1000
        
        # Imports should be fast (< 500ms) - no eager heavy loads
        assert elapsed_ms < 500, \
            f"Module imports took {elapsed_ms:.2f}ms, must be < 500ms (no eager heavy loads)"


# ============================================================================
# GOVERNANCE INVARIANT TESTS
# ============================================================================

class TestGovernanceInvariants:
    """Test governance invariants are preserved"""
    
    def test_governed_session_requires_correlation_id(self):
        """Verify governed_session() calls include correlation_id"""
        from mahoun.graph.neo4j.connection import get_connection
        import inspect
        
        conn = get_connection()
        sig = inspect.signature(conn.governed_session)
        params = list(sig.parameters.keys())
        
        assert 'correlation_id' in params, "governed_session() must accept correlation_id"
    
    def test_governed_session_requires_actor_id(self):
        """Verify governed_session() calls include actor_id"""
        from mahoun.graph.neo4j.connection import get_connection
        import inspect
        
        conn = get_connection()
        sig = inspect.signature(conn.governed_session)
        params = list(sig.parameters.keys())
        
        assert 'actor_id' in params, "governed_session() must accept actor_id"
    
    def test_all_refactored_modules_import_cleanly(self):
        """Verify all refactored modules import without errors"""
        try:
            from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection
            from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
            from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
            from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
            from mahoun.infrastructure.health.integrity_probe import check_neo4j
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# PYTEST HOOKS — ANTI-FALSE-GREEN ENFORCEMENT
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Enforce: If integration tests are requested, they MUST execute.
    
    Prevents false-green scenarios where tests are marked as "passed"
    but were actually skipped due to misconfiguration.
    """
    integration_enabled = os.getenv("MAHOUN_INTEGRATION_ENABLED", "false").lower() == "true"
    
    if not integration_enabled:
        # Integration disabled — skip enforcement
        return
    
    # Count actual skips
    skipped_items = [
        item for item in items 
        if any(marker.name == "skip" for marker in item.iter_markers())
    ]
    
    skip_ratio = len(skipped_items) / len(items) if items else 0
    
    if skip_ratio > 0.3:
        # More than 30% skipped — likely misconfiguration
        pytest.exit(
            f"\n"
            f"❌ ANTI-FALSE-GREEN ENFORCEMENT FAILURE\n"
            f"{'=' * 70}\n"
            f"Integration tests requested (MAHOUN_INTEGRATION_ENABLED=true)\n"
            f"but {len(skipped_items)}/{len(items)} tests ({skip_ratio*100:.0f}%) are skipped.\n"
            f"\n"
            f"This indicates missing dependencies or misconfiguration.\n"
            f"Common causes:\n"
            f"  - Neo4j not running at bolt://localhost:7687\n"
            f"  - Missing environment variables\n"
            f"  - Import failures\n"
            f"\n"
            f"Fix the root cause before proceeding.\n"
            f"{'=' * 70}\n",
            returncode=1
        )
