"""
Adversarial tests for GNNGraphBuilder governance hardening (P0.1)

Two-tier test strategy:
1. Static proof test - always runs, verifies source code patterns
2. Behavioral tests - run only if torch_geometric is available
"""

import importlib.util
import pathlib
import re
import pytest
from unittest.mock import patch, MagicMock

TORCH_GEO_AVAILABLE = importlib.util.find_spec("torch_geometric") is not None

SRC_PATH = pathlib.Path(__file__).parent.parent / "mahoun" / "graph" / "gnn" / "gnn_graph_builder.py"


class TestGNNGraphBuilderStaticProof:
    """P0.1 Static proof: source code analysis for governance patterns."""

    @pytest.mark.p2
    def test_no_raw_driver_creation_patterns_in_source(self):
        """Source must not contain raw Neo4j driver creation patterns."""
        source = SRC_PATH.read_text()

        forbidden_patterns = [
            r"GraphDatabase\.driver\s*=",
            r"from neo4j import GraphDatabase",
            r"\.session\s*\(\)",
            r"\.run\s*\(",
            r"tx\.run\s*\(",
        ]

        for pattern in forbidden_patterns:
            match = re.search(pattern, source)
            assert not match, f"Forbidden pattern found: {pattern}"

    @pytest.mark.p2
    def test_governance_patterns_present_in_source(self):
        """Source must contain governance-required patterns."""
        source = SRC_PATH.read_text()

        required_patterns = [
            "get_connection",
            "governed_session",
            "correlation_id",
            "actor_id",
            "allow_destructive",
        ]

        for pattern in required_patterns:
            assert pattern in source, f"Required pattern missing: {pattern}"


@pytest.mark.skipif(not TORCH_GEO_AVAILABLE, reason="torch_geometric not installed")
class TestGNNGraphBuilderGovernance:
    """P0.1 - Direct driver bypass closed. All writes go through governed_session."""

    @pytest.fixture
    def builder(self):
        from mahoun.graph.gnn.gnn_graph_builder import GNNGraphBuilder
        return GNNGraphBuilder()

    @pytest.mark.p2
    def test_no_raw_driver_creation_possible(self, builder):
        """The class must never create a raw neo4j driver after P0.1."""
        builder_with_uri = type(builder)(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
        )
        assert builder_with_uri.neo4j_driver is None

    @pytest.mark.p2
    def test_save_to_neo4j_requires_governance_params(self, builder):
        """Must fail closed without correlation_id and actor_id."""
        dummy_data = MagicMock()
        dummy_data.doc_ids = []
        dummy_documents = []

        with pytest.raises(ValueError, match="correlation_id and actor_id are mandatory"):
            builder.save_to_neo4j(dummy_data, dummy_documents, "", "actor")

        with pytest.raises(ValueError, match="correlation_id and actor_id are mandatory"):
            builder.save_to_neo4j(dummy_data, dummy_documents, "corr", "")

    @pytest.mark.p2
    def test_governed_session_is_used(self, builder):
        """Must call get_connection().governed_session with correct provenance."""
        dummy_data = MagicMock()
        dummy_data.doc_ids = ["d1"]
        dummy_data.x = [[0.1]]
        dummy_data.edge_index = MagicMock(shape=(2, 0))
        dummy_documents = [{"text": "test"}]

        with patch("mahoun.graph.neo4j.connection.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_gsession = MagicMock()
            mock_tx = MagicMock()
            mock_gsession.begin_transaction.return_value = mock_tx
            mock_conn.governed_session.return_value.__enter__.return_value = mock_gsession
            mock_get_conn.return_value = mock_conn

            builder.save_to_neo4j(
                dummy_data,
                dummy_documents,
                correlation_id="corr-42",
                actor_id="actor-7",
                allow_destructive=False,
            )

            mock_conn.governed_session.assert_called_once_with(
                correlation_id="corr-42", actor_id="actor-7"
            )
            mock_gsession.begin_transaction.assert_called_once()

    @pytest.mark.p2
    def test_destructive_wipe_gated(self, builder):
        """DETACH DELETE must only execute when allow_destructive=True."""
        dummy_data = MagicMock()
        dummy_data.doc_ids = ["d1"]
        dummy_data.x = [[0.1]]
        dummy_data.edge_index = MagicMock(shape=(2, 0))
        dummy_documents = [{"text": "test"}]

        with patch("mahoun.graph.neo4j.connection.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_gsession = MagicMock()
            mock_tx = MagicMock()
            mock_gsession.begin_transaction.return_value = mock_tx
            mock_conn.governed_session.return_value.__enter__.return_value = mock_gsession
            mock_get_conn.return_value = mock_conn

            builder.save_to_neo4j(
                dummy_data, dummy_documents,
                correlation_id="c1", actor_id="a1",
                allow_destructive=False
            )

            wipe_calls = [
                c for c in mock_gsession._execute_authorized.call_args_list
                if "DETACH DELETE" in str(c)
            ]
            assert len(wipe_calls) == 0

            builder.save_to_neo4j(
                dummy_data, dummy_documents,
                correlation_id="c2", actor_id="a2",
                allow_destructive=True
            )

            wipe_calls = [
                c for c in mock_gsession._execute_authorized.call_args_list
                if "DETACH DELETE" in str(c)
            ]
            assert len(wipe_calls) == 1