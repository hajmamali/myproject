"""
P0.2 GOVERNANCE HARDENING TESTS — Graph Query Service

Two-tier test strategy:
1. Static proof test - always runs, verifies source code patterns
2. Behavioral tests - run only when torch_geometric is available
"""

import importlib.util
import pathlib
import re
import pytest
from unittest.mock import patch, MagicMock

TORCH_GEO_AVAILABLE = importlib.util.find_spec("torch_geometric") is not None

SRC_PATH = pathlib.Path(__file__).parent.parent / "mahoun" / "graph" / "graph_query_service.py"


class TestGraphQueryServiceStaticProof:
    """P0.2 Static proof: source code analysis for governance patterns."""

    @pytest.mark.p2
    def test_no_graphdatabase_driver_in_source(self):
        """Source must not contain GraphDatabase.driver."""
        source = SRC_PATH.read_text()
        pattern = r"GraphDatabase\.driver"
        match = re.search(pattern, source)
        assert not match, f"Forbidden pattern found: {pattern}"

    @pytest.mark.p2
    def test_no_direct_session_run_in_source(self):
        """Source must not contain direct session.run() outside governed_session."""
        source = SRC_PATH.read_text()
        forbidden = [
            r"with self\._driver\.session",
            r"(?<!g)session\.run\s*\(",
        ]
        for pattern in forbidden:
            match = re.search(pattern, source)
            assert not match, f"Forbidden pattern found: {pattern}"

    @pytest.mark.p2
    def test_governed_session_present_in_source(self):
        """Source must contain governed_session usage."""
        source = SRC_PATH.read_text()
        assert "governed_session" in source, "governed_session pattern missing"

    @pytest.mark.p2
    def test_get_connection_present_in_source(self):
        """Source must use get_connection for Neo4j access."""
        source = SRC_PATH.read_text()
        assert "get_connection" in source, "get_connection pattern missing"

    @pytest.mark.p2
    def test_classify_query_present_in_source(self):
        """Source must contain classify_query function."""
        source = SRC_PATH.read_text()
        assert "def classify_query" in source, "classify_query function missing"

    @pytest.mark.p2
    def test_enforce_governance_present_in_source(self):
        """Source must contain enforce_governance function."""
        source = SRC_PATH.read_text()
        assert "def enforce_governance" in source, "enforce_governance function missing"


@pytest.mark.skipif(not TORCH_GEO_AVAILABLE, reason="torch_geometric not installed")
class TestGraphQueryServiceGovernance:
    """P0.2 Behavioral tests for governance enforcement."""

    @pytest.fixture
    def service(self):
        from mahoun.graph.graph_query_service import GraphQueryService
        return GraphQueryService()

    @pytest.mark.p2
    def test_read_query_allowed_under_governance(self, service):
        """READ queries should work under governed_session."""
        with patch("mahoun.graph.graph_query_service.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_gsession = MagicMock()
            mock_gsession.run.return_value = []
            mock_conn.governed_session.return_value.__enter__.return_value = mock_gsession
            mock_get_conn.return_value = mock_conn

            result = service.query("MATCH (n) RETURN n LIMIT 10")

            mock_conn.governed_session.assert_called_once()
            assert result.results == []

    @pytest.mark.p2
    def test_write_requires_governance_params(self, service):
        """WRITE queries should require governance params."""
        with patch("mahoun.graph.graph_query_service.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_gsession = MagicMock()
            mock_gsession.run.return_value = []
            mock_conn.governed_session.return_value.__enter__.return_value = mock_gsession
            mock_get_conn.return_value = mock_conn

            result = service.query(
                "CREATE (n:Test {id: $id})",
                params={"id": "123"},
                correlation_id="test",
                actor_id="user"
            )

            mock_conn.governed_session.assert_called_once_with(
                correlation_id="test",
                actor_id="user"
            )

    @pytest.mark.p2
    def test_no_raw_driver_in_connection_manager(self, service):
        """Connection manager should not have direct driver attribute."""
        assert not hasattr(service._connection, '_driver') or service._connection._driver is None
    
    @pytest.mark.p2
    def test_execute_query_propagates_governance_error(self, service):
        """execute_query should raise GovernanceError for WRITE without params."""
        from mahoun.graph.graph_query_service import GovernanceError
        with pytest.raises(GovernanceError):
            service.execute_query(
                "CREATE (n:Node)",
                params={"id": "123"},
                correlation_id=None,
                actor_id=None
            )
    
    @pytest.mark.p2
    def test_execute_query_graceful_for_read(self, service):
        """execute_query should return [] for READ without params (graceful)."""
        with patch("mahoun.graph.graph_query_service.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_gsession = MagicMock()
            mock_gsession.run.return_value = []
            mock_conn.governed_session.return_value.__enter__.return_value = mock_gsession
            mock_get_conn.return_value = mock_conn
            
            result = service.execute_query("MATCH (n) RETURN n LIMIT 10")
            assert result == []


class TestQueryClassification:
    """Tests for query classification engine."""

    @pytest.mark.p2
    def test_classify_read_query(self):
        from mahoun.graph.graph_query_service import classify_query, QueryType
        assert classify_query("MATCH (n) RETURN n") == QueryType.READ
        assert classify_query("OPTIONAL MATCH (n)-[:R]->(m)") == QueryType.READ

    @pytest.mark.p2
    def test_classify_write_query(self):
        from mahoun.graph.graph_query_service import classify_query, QueryType
        assert classify_query("CREATE (n:Node)") == QueryType.WRITE
        assert classify_query("MERGE (n:Node)") == QueryType.WRITE
        assert classify_query("SET n.prop = 'value'") == QueryType.WRITE

    @pytest.mark.p2
    def test_classify_destructive_query(self):
        from mahoun.graph.graph_query_service import classify_query, QueryType
        assert classify_query("DETACH DELETE n") == QueryType.DESTRUCTIVE
        assert classify_query("DELETE ALL") == QueryType.DESTRUCTIVE
        assert classify_query("DROP GRAPH g") == QueryType.DESTRUCTIVE

    @pytest.mark.p2
    def test_classify_destructive_delete_without_where(self):
        from mahoun.graph.graph_query_service import classify_query, QueryType
        assert classify_query("MATCH (n) DELETE n") == QueryType.DESTRUCTIVE

    @pytest.mark.p2
    def test_classify_unknown_query(self):
        from mahoun.graph.graph_query_service import classify_query, QueryType
        assert classify_query("") == QueryType.UNKNOWN


class TestGovernanceEnforcement:
    """Tests for governance enforcement."""

    @pytest.mark.p2
    def test_read_query_allowed_without_params(self):
        from mahoun.graph.graph_query_service import enforce_governance, QueryType, GovernanceError
        enforce_governance(QueryType.READ, None, None)

    @pytest.mark.p2
    def test_write_rejects_missing_params(self):
        from mahoun.graph.graph_query_service import enforce_governance, QueryType, GovernanceError
        with pytest.raises(GovernanceError, match="correlation_id and actor_id"):
            enforce_governance(QueryType.WRITE, None, None)

    @pytest.mark.p2
    def test_destructive_requires_allow_destructive(self):
        from mahoun.graph.graph_query_service import enforce_governance, QueryType, GovernanceError
        with pytest.raises(GovernanceError, match="allow_destructive=True"):
            enforce_governance(QueryType.DESTRUCTIVE, "corr", "actor", allow_destructive=False)

    @pytest.mark.p2
    def test_destructive_allowed_with_all_params(self):
        from mahoun.graph.graph_query_service import enforce_governance, QueryType
        enforce_governance(QueryType.DESTRUCTIVE, "corr", "actor", allow_destructive=True)
    
    @pytest.mark.p2
    def test_write_governance_error_propagates(self):
        from mahoun.graph.graph_query_service import enforce_governance, QueryType, GovernanceError
        with pytest.raises(GovernanceError):
            enforce_governance(QueryType.WRITE, None, None)
    
    @pytest.mark.p2
    def test_destructive_governance_error_propagates(self):
        from mahoun.graph.graph_query_service import enforce_governance, QueryType, GovernanceError
        with pytest.raises(GovernanceError):
            enforce_governance(QueryType.DESTRUCTIVE, "corr", "actor", allow_destructive=False)