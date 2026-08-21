"""
Unit and Security Tests for Governed Knowledge Graph Router
============================================================
Verifies fail-closed Cypher safety, mutation keyword rejection, procedure allowlists,
multi-statement rejection, depth limits, and static driver isolation invariants.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pathlib import Path

from api.main import app
from api.routers.graph import validate_read_only_cypher, PROCEDURE_ALLOWLIST, FORBIDDEN_KEYWORDS

client = TestClient(app)


# =============================================================================
# 1. Cypher Read-Only & Fail-Closed Safety Tests
# =============================================================================

def test_valid_read_query_allowed():
    """Verify that pure read-only Cypher queries pass validation."""
    valid_queries = [
        "MATCH (n:Law) RETURN n LIMIT 10",
        "MATCH (a:Article)-[:BELONGS_TO]->(l:Law) WHERE a.number = 1 RETURN a, l",
        "MATCH (v:Verdict) WITH v ORDER BY v.date DESC RETURN v LIMIT 5",
        "CALL db.labels()",
        "CALL db.relationshipTypes()",
    ]
    for q in valid_queries:
        validate_read_only_cypher(q)  # Should not raise


def test_create_query_rejected():
    """Verify CREATE operations are strictly rejected with 403."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("CREATE (n:Law {name: 'Malicious'}) RETURN n")
    assert exc_info.value.status_code == 403


def test_merge_query_rejected():
    """Verify MERGE operations are strictly rejected with 403."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("MERGE (n:Law {id: '123'}) ON CREATE SET n.created = 1 RETURN n")
    assert exc_info.value.status_code == 403


def test_delete_query_rejected():
    """Verify DELETE / DETACH DELETE operations are strictly rejected with 403."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("MATCH (n:Law) DETACH DELETE n")
    assert exc_info.value.status_code == 403


def test_set_query_rejected():
    """Verify SET property mutations are strictly rejected with 403."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("MATCH (n:Law) SET n.hacked = true RETURN n")
    assert exc_info.value.status_code == 403


def test_remove_query_rejected():
    """Verify REMOVE property/label mutations are strictly rejected with 403."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("MATCH (n:Law) REMOVE n.secret RETURN n")
    assert exc_info.value.status_code == 403


def test_call_procedure_rejected_unless_allowlisted():
    """Verify non-allowlisted procedure calls (APOC, custom) are rejected."""
    forbidden_calls = [
        "CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'DELETE n', {batchSize:100})",
        "CALL apoc.export.csv.all('out.csv', {})",
        "CALL dbms.security.createUser('hacker', 'pass')",
    ]
    for q in forbidden_calls:
        with pytest.raises(HTTPException) as exc_info:
            validate_read_only_cypher(q)
        assert exc_info.value.status_code == 403


def test_multi_statement_rejected():
    """Verify semicolon-delimited multi-statement queries are strictly rejected."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("MATCH (n) RETURN n; MATCH (m) DETACH DELETE m")
    assert exc_info.value.status_code == 403


def test_empty_query_rejected():
    """Verify empty query string is rejected with 400."""
    with pytest.raises(HTTPException) as exc_info:
        validate_read_only_cypher("   ")
    assert exc_info.value.status_code == 400


# =============================================================================
# 2. HTTP Endpoint Tests
# =============================================================================

def test_query_endpoint_mutation_rejection():
    """Test POST /api/v1/graph/query rejects mutation payloads via HTTP."""
    payload = {
        "query": "CREATE (n:TestNode {name: 'Test'}) RETURN n",
        "limit": 10
    }
    response = client.post("/api/v1/graph/query", json=payload)
    assert response.status_code in (403, 500)  # Fails closed


def test_expand_endpoint_depth_limit():
    """Test POST /api/v1/graph/expand rejects depth > 3 via schema validation."""
    payload = {
        "node_id": "law_001",
        "depth": 10  # Exceeds max 3
    }
    response = client.post("/api/v1/graph/expand", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_quality_metrics_endpoint():
    """Test GET /api/v1/graph/quality/metrics returns 200 and deterministic structure."""
    response = client.get("/api/v1/graph/quality/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "quality_score" in data
    assert "quality_level" in data
    assert "total_nodes" in data
    assert "total_edges" in data


def test_integrity_issues_endpoint():
    """Test GET /api/v1/graph/integrity/issues returns 200 and issue summary."""
    response = client.get("/api/v1/graph/integrity/issues")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "issues" in data
    assert "summary" in data


def test_completeness_report_endpoint():
    """Test GET /api/v1/graph/completeness/report returns 200 and completeness metrics."""
    response = client.get("/api/v1/graph/completeness/report")
    assert response.status_code == 200
    data = response.json()
    assert "completeness_percentage" in data
    assert "total_entities" in data


# =============================================================================
# 3. Architectural Invariants
# =============================================================================

def test_no_unauthorized_driver_in_graph_router():
    """Architectural Guard: api/routers/graph.py MUST NOT instantiate drivers directly."""
    router_path = Path(__file__).resolve().parent.parent.parent / "api" / "routers" / "graph.py"
    assert router_path.exists(), "api/routers/graph.py must exist"
    
    content = router_path.read_text(encoding="utf-8")
    assert "GraphDatabase.driver" not in content, (
        "Violation: api/routers/graph.py must NOT instantiate GraphDatabase.driver directly"
    )
    assert "AsyncGraphDatabase.driver" not in content, (
        "Violation: api/routers/graph.py must NOT instantiate AsyncGraphDatabase.driver directly"
    )
