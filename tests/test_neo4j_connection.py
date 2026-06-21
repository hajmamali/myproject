"""
Tests for Neo4j Connection Management
"""
import pytest
pytest.importorskip("neo4j")

from mahoun.graph.neo4j.connection import get_connection
from mahoun.core.governance.violations import GovernanceViolationError

# Skip these tests by default - require running Neo4j server
pytestmark = pytest.mark.integration


@pytest.fixture
def connection():
    """Get Neo4j connection for testing"""
    conn = get_connection()
    yield conn


def test_connection_initialization(connection):
    """Test connection initialization"""
    assert connection is not None
    assert connection.driver is not None
    assert connection.database == "neo4j"


def test_verify_connectivity(connection):
    """Test connection verification"""
    is_connected = connection.verify_connectivity()
    assert is_connected is True


def test_execute_query(connection):
    """Test executing a simple query"""
    result = connection.execute_query("RETURN 1 AS num")
    assert len(result) == 1
    assert result[0]["num"] == 1


def test_execute_batch(connection):
    """Test executing batch queries"""
    # execute_batch has been constitutionally abolished to prevent bypasses.
    queries = [
        ("CREATE (n:TestBatch {id: $id, name: $name})", {"id": f"test_{i}", "name": f"Test {i}"})
        for i in range(5)
    ]
    
    with pytest.raises(GovernanceViolationError, match="execute_batch.*constitutionally forbidden"):
        connection.execute_batch(queries)


def test_health_check(connection):
    """Test health check"""
    health = connection.health_check()
    
    assert health["status"] == "healthy"
    assert health["connected"] is True
    assert health["response_time_ms"] is not None
    assert health["node_count"] is not None
    assert health["error"] is None


def test_get_database_info(connection):
    """Test getting database information"""
    info = connection.get_database_info()
    
    assert "node_count" in info
    assert "relationship_count" in info
    assert "labels" in info
    assert "relationship_types" in info
    assert info["database"] == "neo4j"


def test_session_context_manager(connection):
    """Test session context manager"""
    with connection.session() as session:
        result = session.run("RETURN 1 AS num")
        record = result.single()
        assert record["num"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
