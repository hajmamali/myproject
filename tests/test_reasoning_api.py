"""
Reasoning API Tests
===================

Comprehensive tests for reasoning API endpoints.

Test Coverage:
- Verdict generation endpoint
- Verdict verification endpoint
- Ledger query endpoint
- Health check endpoint
- Error handling
- Resource constraint enforcement
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Import API app
from api.main import app

# Import models for testing
from mahoun.crypto.proof_system import CryptographicProof


@pytest.fixture
def client() -> TestClient:
    """Test client for API"""
    return TestClient(app)


# ============================================================================
# Test: Verdict Generation Endpoint (Integration Tests)
# ============================================================================


def test_generate_verdict_success_integration(client: TestClient) -> None:
    """Test successful verdict generation (integration test)"""
    # Make request with real engine
    response = client.post(
        "/api/v1/reasoning/generate-verdict",
        json={
            "question": "Is contract termination valid?",
            "facts": [
                {"value": "Contract signed on 2024-01-01"},
                {"value": "Termination notice sent on 2024-06-01"},
            ],
            "generate_proof": False,  # Skip proof for faster test
        },
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "verdict_id" in data
    assert "case_id" in data
    assert "final_verdict" in data
    assert len(data["steps"]) >= 1  # At least one step
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert isinstance(data["unresolved_conflicts"], list)


def test_generate_verdict_empty_facts(client: TestClient) -> None:
    """Test verdict generation with empty facts"""
    response = client.post(
        "/api/v1/reasoning/generate-verdict",
        json={
            "question": "Is contract termination valid?",
            "facts": [],
            "generate_proof": False,
        },
    )

    # Should succeed with empty facts
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_generate_verdict_invalid_request(client: TestClient) -> None:
    """Test verdict generation with invalid request"""
    # Missing required field
    response = client.post(
        "/api/v1/reasoning/generate-verdict",
        json={
            "facts": [{"value": "Contract signed"}]
            # Missing "question"
        },
    )

    # Should return 422 (validation error)
    assert response.status_code == 422


# ============================================================================
# Test: Verdict Verification Endpoint
# ============================================================================


@patch("api.routers.reasoning.get_keypair")
def test_verify_verdict_success(mock_keypair: MagicMock, client: TestClient) -> None:
    """Test successful verdict verification"""
    # Setup mock
    mock_keypair.return_value = ("private_key", "public_key")

    # Create a valid proof
    from mahoun.crypto.signatures import generate_keypair

    private_key, public_key = generate_keypair()

    # Mock proof data
    proof_data = {
        "graph_state_hash": "a" * 64,
        "reasoning_chain_hash": "b" * 64,
        "evidence_merkle_root": "c" * 64,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signature": "d" * 128,
        "verdict_id": "verdict_123",
        "case_id": "case_456",
        "confidence": 0.95,
    }

    # Mock proof.verify() to return True
    with patch.object(CryptographicProof, "verify", return_value=True):
        response = client.post(
            "/api/v1/reasoning/verify-verdict",
            json={"verdict_id": "verdict_123", "proof": proof_data},
        )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["verdict_id"] == "verdict_123"
    assert data["is_valid"] is True
    assert "verification_details" in data


# ============================================================================
# Test: Ledger Query Endpoint
# ============================================================================


def test_query_ledger_not_found(client: TestClient) -> None:
    """Test ledger query with no results"""
    response = client.post(
        "/api/v1/reasoning/query-ledger", json={"verdict_id": "nonexistent"}
    )

    # Should return empty results
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_count"] == 0
    assert len(data["entries"]) == 0


# ============================================================================
# Test: Health Check Endpoint
# ============================================================================


@patch("api.routers.reasoning.is_desktop_minimal")
@patch("api.routers.reasoning.should_skip_graph")
def test_health_check_unavailable_mode(
    mock_skip_graph: MagicMock, mock_desktop: MagicMock, client: TestClient
) -> None:
    """Test health check in unavailable mode"""
    # Setup mocks
    mock_desktop.return_value = True
    mock_skip_graph.return_value = True

    # Make request
    response = client.get("/api/v1/reasoning/health")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "unavailable"
    assert data["mode"] == "DESKTOP_MINIMAL"
    assert data["graph_enabled"] is False


@patch("api.routers.reasoning.is_desktop_minimal")
@patch("api.routers.reasoning.should_skip_graph")
def test_health_check_healthy(
    mock_skip_graph: MagicMock, mock_desktop: MagicMock, client: TestClient
) -> None:
    """Test health check in healthy state"""
    # Setup mocks
    mock_desktop.return_value = False
    mock_skip_graph.return_value = False

    # Make request
    response = client.get("/api/v1/reasoning/health")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["mode"] == "ENTERPRISE_FULL"
    assert data["graph_enabled"] is True
    assert "components" in data


# ============================================================================
# Test: Error Handling
# ============================================================================


def test_error_response_structure(client: TestClient) -> None:
    """Test that error responses have consistent structure"""
    # Trigger validation error
    response = client.post(
        "/api/v1/reasoning/generate-verdict",
        json={},  # Empty request
    )

    # Should have consistent error structure
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data  # FastAPI validation error format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
