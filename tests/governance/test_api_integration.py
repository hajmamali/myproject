"""
Tests for API Integration
==========================

Classification: CRITICAL INTEGRATION TESTS
Purpose: Verify API integration with governance and proof-carrying responses

NOTE: These tests use mocked verdict engine to focus on governance integration
rather than actual verdict generation (which requires full graph infrastructure).

Test Coverage:
- Verdict generation
- Verdict verification
- Ledger query
- Health check
- Error handling
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from mahoun.core.governance import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError

# ============================================================================
# MOCK VERDICT ENGINE
# ============================================================================


class MockVerdictStep:
    """Mock verdict step"""

    def __init__(self, conclusion: str, evidence: list, confidence: float = 0.95):
        self.conclusion = conclusion
        self.evidence = evidence
        self.confidence = confidence


class MockEvidenceLinkedVerdict:
    """Mock verdict result"""

    def __init__(self):
        self.final_verdict = "Tax exemption applies"
        self.confidence_score = 0.92
        self.verdict_id = "verdict-001"
        self.steps = [
            MockVerdictStep(conclusion="Entity is non-profit", evidence=["node_1", "node_2"], confidence=0.95),
            MockVerdictStep(conclusion="Activity is charitable", evidence=["node_3", "node_4"], confidence=0.90),
            MockVerdictStep(conclusion="Tax exemption applies", evidence=["node_5", "node_6"], confidence=0.92),
        ]


# ============================================================================
# ============================================================================
# MOCK VERDICT ENGINE
# ============================================================================


@pytest.fixture
def mock_verdict_engine():
    """Create a mock verdict engine that returns valid responses"""
    from dataclasses import dataclass, field
    from typing import Any

    @dataclass
    class MockVerdictStep:
        conclusion: str
        evidence: list[str] = field(default_factory=list)
        confidence: float = 0.92

    @dataclass
    class MockVerdict:
        final_verdict: str
        steps: list[MockVerdictStep]
        confidence_score: float
        verdict_id: str
        unresolved_conflicts: list[str] = field(default_factory=list)
        ledger_hash: str = "mock_hash_123"

    from mahoun.core.governance.violations import (
        GovernanceViolation,
        ViolationCategory,
        ViolationSeverity,
    )

    async def mock_generate_verdict(question: str, facts: list[Any], case_id: str | None = None):

        try:
            ctx = GovernanceContextManager.require_context()
            correlation_id = ctx.correlation_id
        except Exception:
            correlation_id = None

        if correlation_id == "case-002":
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.GOVERNANCE_BYPASS,
                    severity=ViolationSeverity.CRITICAL,
                    message="Governance context is inactive or invalid",
                    details={},
                    source="mock_verdict_engine",
                    correlation_id=correlation_id,
                )
            )

        if not facts:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_EVIDENCE,
                    severity=ViolationSeverity.CRITICAL,
                    message="Reasoning requires evidence/facts",
                    details={},
                    source="mock_verdict_engine",
                    correlation_id=correlation_id,
                )
            )

        # Create realistic verdict with steps
        steps = [
            MockVerdictStep(
                conclusion="Entity qualifies as non-profit", evidence=["node_1", "node_2"], confidence=0.95
            ),
            MockVerdictStep(
                conclusion="Activity is charitable in nature", evidence=["node_3", "node_4"], confidence=0.90
            ),
            MockVerdictStep(conclusion="Tax exemption applies", evidence=["node_5", "node_6"], confidence=0.92),
        ]

        return MockVerdict(
            final_verdict="Tax exemption applies", steps=steps, confidence_score=0.92, verdict_id="verdict_123"
        )

    mock_engine = MagicMock()
    mock_engine.generate_verdict = mock_generate_verdict
    return mock_engine


# ============================================================================
# TEST CLIENT
# ============================================================================


@pytest.fixture
def client(mock_verdict_engine):
    """Create test client with mocked verdict engine"""
    from api.routers.reasoning import get_verdict_engine

    app.dependency_overrides[get_verdict_engine] = lambda: mock_verdict_engine
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ============================================================================
# TESTS: Verdict Generation
# ============================================================================


class TestVerdictGeneration:
    """Tests for verdict generation endpoint"""

    @pytest.mark.p0
    def test_generate_verdict_success(self, client):
        """Test successful verdict generation with high-quality evidence"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Is tax exemption applicable?",
                "facts": [
                    {
                        "value": "Entity is registered as non-profit organization under section 501(c)(3)",
                        "type": "FACT",
                        "confidence": 1.0,
                    },
                    {
                        "value": "Entity's primary activity is charitable education and community service",
                        "type": "FACT",
                        "confidence": 1.0,
                    },
                    {
                        "value": "Entity has no political lobbying or campaign activities",
                        "type": "FACT",
                        "confidence": 1.0,
                    },
                    {
                        "value": "Entity's funds are exclusively used for exempt purposes",
                        "type": "FACT",
                        "confidence": 1.0,
                    },
                    {
                        "value": "Entity has obtained IRS determination letter confirming tax-exempt status",
                        "type": "FACT",
                        "confidence": 1.0,
                    },
                ],
                "case_id": "case-001",
                "generate_proof": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "verdict_id" in data
        assert "case_id" in data
        assert "final_verdict" in data
        assert "steps" in data
        assert "confidence_score" in data
        # Proof-carrying contract fields are at top level, not in proof
        assert data["fortress_validated"] is True
        assert "audit_hash" in data
        assert "validation_timestamp" in data
        assert "correlation_id" in data
        # Cryptographic proof is separate
        assert "proof" in data

    @pytest.mark.p0
    def test_generate_verdict_without_governance_context(self, client):
        """Test verdict generation without governance context"""
        from mahoun.core.fortress_validator import SecurityBreachException, ViolationType, ViolationSeverity
        from unittest.mock import patch

        with patch("api.routers.reasoning.get_governance_context") as mock_get_ctx:
            mock_get_ctx.side_effect = SecurityBreachException(
                message="GovernanceContext not found in request.state",
                violation_type=ViolationType.MISSING_EVIDENCE,
                severity=ViolationSeverity.CRITICAL,
                forensic_context={"error": "SECURITY_BREACH", "correlation_id": "test-err"},
                correlation_id="test-err",
            )
            response = client.post(
                "/api/v1/reasoning/generate-verdict",
                json={
                    "question": "Is tax exemption applicable?",
                    "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                    "case_id": "case-002",
                    "generate_proof": True,
                },
            )

            # Should return 403 (governance breach converted to controlled HTTP response)
            assert response.status_code == 403
            body = response.json()
            error_name = body.get("error") or (body.get("detail", {}).get("error") if isinstance(body.get("detail"), dict) else None)
            assert error_name and error_name.upper() == "SECURITY_BREACH"

    @pytest.mark.p0
    def test_generate_verdict_with_invalid_facts(self, client):
        """Test verdict generation with invalid facts (empty facts rejected by governance)"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Is tax exemption applicable?",
                "facts": [],  # Empty facts - violates EL-I1/EL-I3
                "case_id": "case-003",
                "generate_proof": True,
            },
        )

        # FortressValidator correctly rejects verdicts without evidence
        # This is the expected governance-enforced behavior
        # CONTROLLED RESPONSE: Must return 403/422 with structured error payload
        assert response.status_code in (403, 422)
        body = response.json()
        error_name = body.get("error") or (body.get("detail", {}).get("error") if isinstance(body.get("detail"), dict) else None)
        assert (error_name and error_name.upper() in ("SECURITY_BREACH", "MISSING_EVIDENCE")) or "MISSING_EVIDENCE" in str(body)

    @pytest.mark.p0
    def test_generate_verdict_without_proof(self, client):
        """Test verdict generation without proof (generate_proof=False)"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Is tax exemption applicable?",
                "facts": [
                    {"value": "Entity is registered as non-profit organization", "type": "FACT", "confidence": 1.0},
                    {"value": "Entity operates for charitable purposes", "type": "FACT", "confidence": 1.0},
                    {"value": "Entity has no political activities", "type": "FACT", "confidence": 1.0},
                ],
                "case_id": "case-004",
                "generate_proof": False,  # Skip cryptographic proof generation
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # Proof-carrying contract fields still present (fortress validation always happens)
        assert data["fortress_validated"] is True
        # But cryptographic proof may be None if generate_proof=False
        # Note: proof field contains cryptographic proof, not fortress validation


# ============================================================================
# TESTS: Verdict Verification
# ============================================================================


class TestVerdictVerification:
    """Tests for verdict verification endpoint"""

    @pytest.mark.p0
    def test_verify_verdict_success(self, client):
        """Test successful verdict verification"""
        # First generate a verdict with high-quality evidence
        gen_response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Is tax exemption applicable?",
                "facts": [
                    {
                        "value": "Entity is registered as non-profit organization under section 501(c)(3)",
                        "type": "FACT",
                        "confidence": 1.0,
                    },
                    {"value": "Entity's primary activity is charitable education", "type": "FACT", "confidence": 1.0},
                    {"value": "Entity has no political activities", "type": "FACT", "confidence": 1.0},
                ],
                "case_id": "case-005",
                "generate_proof": True,
            },
        )

        assert gen_response.status_code == 200
        gen_data = gen_response.json()

        # Skip verification if proof is not available (mock engine doesn't generate proofs)
        if gen_data.get("proof") is None:
            pytest.skip("Proof not generated by mock engine, skipping verification test")

        # Then verify it
        verify_response = client.post(
            "/api/v1/reasoning/verify-verdict", json={"verdict_id": gen_data["verdict_id"], "proof": gen_data["proof"]}
        )

        assert verify_response.status_code == 200
        data = verify_response.json()

        assert data["success"] is True
        assert "verdict_id" in data
        assert "is_valid" in data
        assert "verification_details" in data
        # Proof-carrying fields are at top level
        assert data["fortress_validated"] is True
        assert "audit_hash" in data

    @pytest.mark.p0
    def test_verify_verdict_with_invalid_proof(self, client):
        """Test verdict verification with invalid proof"""
        response = client.post(
            "/api/v1/reasoning/verify-verdict",
            json={
                "verdict_id": "non-existent",
                "proof": {
                    "graph_state_hash": "invalid",
                    "reasoning_chain_hash": "invalid",
                    "evidence_merkle_root": "invalid",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "signature": "invalid",
                    "verdict_id": "non-existent",
                    "case_id": "non-existent",
                    "confidence": 0.92,
                },
            },
        )

        # Should return validation error
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False


# ============================================================================
# TESTS: Ledger Query
# ============================================================================


class TestLedgerQuery:
    """Tests for ledger query endpoint"""

    @pytest.mark.p0
    def test_query_ledger_by_verdict_id(self, client):
        """Test querying ledger by verdict_id"""
        response = client.post("/api/v1/reasoning/query-ledger", json={"verdict_id": "non-existent-verdict"})

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "entries" in data
        assert "total_count" in data
        # Proof-carrying fields are at top level
        assert data["fortress_validated"] is True
        assert "audit_hash" in data

    @pytest.mark.p0
    def test_query_ledger_by_case_id(self, client):
        """Test querying ledger by case_id"""
        response = client.post("/api/v1/reasoning/query-ledger", json={"case_id": "non-existent-case"})

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "entries" in data
        assert "total_count" in data

    @pytest.mark.p0
    def test_query_ledger_by_node_id(self, client):
        """Test querying ledger by node_id"""
        response = client.post("/api/v1/reasoning/query-ledger", json={"node_id": "non-existent-node"})

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "entries" in data
        assert "total_count" in data

    @pytest.mark.p0
    def test_query_ledger_by_time_range(self, client):
        """Test querying ledger by time range"""
        response = client.post(
            "/api/v1/reasoning/query-ledger",
            json={"start_time": "2025-01-01T00:00:00Z", "end_time": "2025-12-31T23:59:59Z"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "entries" in data
        assert "total_count" in data


# ============================================================================
# TESTS: Health Check
# ============================================================================


class TestHealthCheck:
    """Tests for health check endpoint"""

    @pytest.mark.p0
    def test_health_check_success(self, client):
        """Test successful health check"""
        response = client.get("/api/v1/reasoning/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "mode" in data
        assert "graph_enabled" in data
        assert "components" in data
        assert "timestamp" in data

    @pytest.mark.p0
    def test_health_check_desktop_minimal_mode(self, client):
        """Test health check in DESKTOP_MINIMAL mode"""
        # This test may need environment variable setup
        response = client.get("/api/v1/reasoning/health")

        assert response.status_code == 200
        data = response.json()

        # Should return either healthy or unavailable
        assert data["status"] in ["healthy", "unavailable"]


# ============================================================================
# TESTS: Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.p0
    def test_generate_verdict_with_missing_question(self, client):
        """Test verdict generation with missing question"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-006",
                "generate_proof": True,
            },
        )

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.p0
    def test_generate_verdict_with_missing_facts(self, client):
        """Test verdict generation with missing facts"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={"question": "Test question", "case_id": "case-007", "generate_proof": True},
        )

        # Should return validation error (facts is required)
        assert response.status_code == 422

    @pytest.mark.p0
    def test_generate_verdict_with_empty_question(self, client):
        """Test verdict generation with empty question"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "",
                "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-008",
                "generate_proof": True,
            },
        )

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.p0
    def test_verify_verdict_with_missing_verdict_id(self, client):
        """Test verdict verification with missing verdict_id"""
        response = client.post(
            "/api/v1/reasoning/verify-verdict",
            json={
                "proof": {
                    "graph_state_hash": "hash",
                    "reasoning_chain_hash": "hash",
                    "evidence_merkle_root": "hash",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "signature": "sig",
                    "verdict_id": "test",
                    "case_id": "test",
                    "confidence": 0.92,
                }
            },
        )

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.p0
    def test_query_ledger_with_invalid_time_range(self, client):
        """Test ledger query with invalid time range"""
        response = client.post(
            "/api/v1/reasoning/query-ledger", json={"start_time": "invalid-date", "end_time": "invalid-date"}
        )

        # Should return validation error (deterministic)
        assert response.status_code in (400, 422)


# ============================================================================
# TESTS: Proof-Carrying Response Validation
# ============================================================================


class TestProofCarryingResponse:
    """Tests for proof-carrying response validation"""

    @pytest.mark.p0
    def test_all_responses_include_proof_carrying_fields(self, client):
        """Test that all responses include proof-carrying fields"""
        # Generate verdict
        gen_response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Test question",
                "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-009",
                "generate_proof": True,
            },
        )

        assert gen_response.status_code == 200
        gen_data = gen_response.json()

        # Verify proof-carrying fields
        assert gen_data["fortress_validated"] is True
        assert "audit_hash" in gen_data
        assert len(gen_data["audit_hash"]) >= 16
        assert len(gen_data["audit_hash"]) <= 64
        assert "validation_timestamp" in gen_data
        assert "correlation_id" in gen_data

        # Verify timestamp is ISO 8601
        timestamp = gen_data["validation_timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    @pytest.mark.p0
    def test_verification_response_includes_proof_carrying(self, client):
        """Test that verification response includes proof-carrying fields"""
        # Generate verdict
        gen_response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Test question",
                "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-010",
                "generate_proof": True,
            },
        )

        assert gen_response.status_code == 200
        gen_data = gen_response.json()

        # Skip verification if proof is not available (mock engine doesn't generate proofs)
        if gen_data.get("proof") is None:
            pytest.skip("Proof not generated by mock engine, skipping verification test")

        # Verify verdict
        verify_response = client.post(
            "/api/v1/reasoning/verify-verdict", json={"verdict_id": gen_data["verdict_id"], "proof": gen_data["proof"]}
        )

        assert verify_response.status_code == 200
        verify_data = verify_response.json()

        # Verify proof-carrying fields
        assert verify_data["fortress_validated"] is True
        assert "audit_hash" in verify_data

    @pytest.mark.p0
    def test_ledger_query_response_includes_proof_carrying(self, client):
        """Test that ledger query response includes proof-carrying fields"""
        response = client.post("/api/v1/reasoning/query-ledger", json={"case_id": "test-case"})

        assert response.status_code == 200
        data = response.json()

        # Verify proof-carrying fields
        assert data["fortress_validated"] is True
        assert "audit_hash" in data


# ============================================================================
# TESTS: Performance
# ============================================================================


class TestPerformance:
    """Tests for API performance"""

    @pytest.mark.p0
    def test_generate_verdict_performance(self, client):
        """Test verdict generation performance"""
        import time

        start = time.time()
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Test question",
                "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-011",
                "generate_proof": True,
            },
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0  # < 5s

    @pytest.mark.p0
    def test_concurrent_requests(self, client):
        """Test concurrent requests"""
        import time

        async def make_request():
            return client.post(
                "/api/v1/reasoning/generate-verdict",
                json={
                    "question": "Test question",
                    "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                    "case_id": f"case-{i}",
                    "generate_proof": True,
                },
            )

        start = time.time()

        # Run 10 concurrent requests
        import threading

        results = []

        def worker(i):
            result = client.post(
                "/api/v1/reasoning/generate-verdict",
                json={
                    "question": "Test question",
                    "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                    "case_id": f"case-{i}",
                    "generate_proof": True,
                },
            )
            results.append(result)

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start

        assert len(results) == 10
        assert elapsed < 10.0  # < 10s for 10 concurrent requests


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.p0
    def test_generate_verdict_with_long_question(self, client):
        """Test verdict generation with long question"""
        long_question = "Test question " * 1000

        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": long_question,
                "facts": [{"value": "Test fact", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-012",
                "generate_proof": True,
            },
        )

        # Should handle long question
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.p0
    def test_generate_verdict_with_many_facts(self, client):
        """Test verdict generation with many facts"""
        facts = [{"value": f"Fact {i}", "type": "FACT", "confidence": 1.0} for i in range(100)]

        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={"question": "Test question", "facts": facts, "case_id": "case-013", "generate_proof": True},
        )

        # Should handle many facts
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.p0
    def test_generate_verdict_with_special_characters(self, client):
        """Test verdict generation with special characters"""
        response = client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Test question with special chars: @#$%^&*()",
                "facts": [{"value": "Fact with émojis 🎯", "type": "FACT", "confidence": 1.0}],
                "case_id": "case-014",
                "generate_proof": True,
            },
        )

        # Should handle special characters
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
