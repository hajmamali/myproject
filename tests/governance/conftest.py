"""
MAHOUN Governance Test Fixtures
================================

Classification: TEST INFRASTRUCTURE
Purpose: Shared fixtures for governance tests

This module provides shared fixtures for all governance tests including:
- GovernanceLock reset
- Valid reasoning response
- FortressValidator instance
- GovernanceContext instance
- ProvenanceAttestation instance
"""

import dataclasses
from datetime import UTC, datetime
from typing import Any

import pytest

from mahoun.core.fortress_validator import (
    ExecutionMode,
    FortressValidator,
    ReasoningResponse,
)
from mahoun.core.governance import (
    GovernanceContextManager,
)
from mahoun.core.governance.provenance_attestation import (
    InferenceProvenance,
    ProvenanceAttestation,
    ProvenanceChain,
    ProvenanceWithAttestation,
)
from mahoun.core.governance_lock import (
    GovernanceLock,
    GovernanceMode,
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def is_frozen_dataclass(instance: Any) -> bool:
    """
    Check if instance is a frozen dataclass.

    CRITICAL: dataclasses.is_frozen() does not exist in Python.
    Must use __dataclass_params__.frozen instead.

    Args:
        instance: Object to check

    Returns:
        True if instance is a frozen dataclass
    """
    if not dataclasses.is_dataclass(instance):
        return False

    # Access frozen parameter from dataclass params
    return instance.__dataclass_params__.frozen


@pytest.fixture
def unfreeze_dataclass():
    """
    Test-only helper: returns a mutable copy of a frozen dataclass.

    CRITICAL: Cannot directly modify frozen dataclasses.
    Use dataclasses.replace() to create modified copy.
    """

    def _unfreeze(instance: Any) -> Any:
        if not is_frozen_dataclass(instance):
            return instance
        return dataclasses.replace(instance)

    return _unfreeze


# ============================================================================
# FIXTURES: GovernanceLock
# ============================================================================


@pytest.fixture(autouse=True)
def reset_governance_lock():
    """Reset governance lock before each test"""
    GovernanceLock._reset()
    yield
    GovernanceLock._reset()


@pytest.fixture
def governance_lock_strict():
    """Initialize GovernanceLock in STRICT mode"""
    GovernanceLock.initialize(mode=GovernanceMode.STRICT)
    return GovernanceLock


@pytest.fixture
def governance_lock_audit():
    """Initialize GovernanceLock in AUDIT mode"""
    GovernanceLock.initialize(mode=GovernanceMode.AUDIT)
    return GovernanceLock


# ============================================================================
# FIXTURES: Valid Reasoning Response
# ============================================================================


class MockProofTree:
    """Mock proof tree for testing"""

    def __init__(self, depth: int = 3):
        self.depth = depth

    def get_proof_depth(self) -> int:
        return self.depth

    def get_proof_size(self) -> int:
        return self.depth * 2


@pytest.fixture
def valid_response() -> ReasoningResponse:
    """Create a valid reasoning response that passes all checks"""
    return ReasoningResponse(
        success=True,
        result="Tax exemption applies under Article 143",
        confidence=0.92,
        reasoning_mode="HYBRID",
        execution_time_ms=245.5,
        proof_tree=MockProofTree(depth=5),
        derived_facts=[
            "tax_exempt(entity_123)",
            "article_143_applies(entity_123)",
            "constitutional_override(article_143, article_505)",
        ],
        metadata={"agreement_score": 0.89},
    )


@pytest.fixture
def valid_response_symbolic() -> ReasoningResponse:
    """Create a valid symbolic-only response"""
    return ReasoningResponse(
        success=True,
        result="Tax exemption applies",
        confidence=0.95,
        reasoning_mode="SYMBOLIC",
        execution_time_ms=150.0,
        proof_tree=MockProofTree(depth=5),
        derived_facts=["tax_exempt(entity_123)"],
        metadata={},
    )


@pytest.fixture
def invalid_response_no_proof() -> ReasoningResponse:
    """Response missing proof_tree (should fail)"""
    return ReasoningResponse(
        success=True,
        result="Tax exemption applies",
        confidence=0.85,
        reasoning_mode="HYBRID",
        execution_time_ms=150.0,
        proof_tree=None,
        derived_facts=["tax_exempt(entity_123)"],
        metadata={"agreement_score": 0.90},
    )


@pytest.fixture
def invalid_response_low_agreement() -> ReasoningResponse:
    """Response with agreement_score below 0.85 threshold"""
    return ReasoningResponse(
        success=True,
        result="Tax exemption applies",
        confidence=0.80,
        reasoning_mode="HYBRID",
        execution_time_ms=200.0,
        proof_tree=MockProofTree(depth=3),
        derived_facts=["tax_exempt(entity_123)"],
        metadata={"agreement_score": 0.65},
    )


# ============================================================================
# FIXTURES: FortressValidator
# ============================================================================


@pytest.fixture
def validator() -> FortressValidator:
    """Create FortressValidator instance"""
    return FortressValidator(execution_mode=ExecutionMode.DESKTOP_MINIMAL, strict_mode=True)


@pytest.fixture
def validator_non_strict() -> FortressValidator:
    """Create non-strict FortressValidator (logs only, no exceptions)"""
    return FortressValidator(execution_mode=ExecutionMode.DESKTOP_MINIMAL, strict_mode=False)


# ============================================================================
# FIXTURES: GovernanceContext
# ============================================================================


@pytest.fixture
def governance_context() -> GovernanceContextManager:
    """Create GovernanceContext instance"""
    return GovernanceContextManager.create_context(correlation_id="test-001", execution_mode="STRICT")


@pytest.fixture
async def active_governance_context():
    """Create active governance context"""
    async with GovernanceContextManager.active_context(correlation_id="test-002", execution_mode="STRICT") as ctx:
        yield ctx


# ============================================================================
# FIXTURES: ProvenanceAttestation
# ============================================================================


@pytest.fixture
def provenance_attestation() -> ProvenanceAttestation:
    """Create ProvenanceAttestation instance"""
    return ProvenanceAttestation.create(
        provenance_data={"source": "test", "correlation_id": "test-001"},
        governance_scope_id="scope-001",
        runtime_attestation_id="attest-001",
    )


@pytest.fixture
def inference_provenance() -> InferenceProvenance:
    """Create InferenceProvenance instance"""
    return InferenceProvenance.create(
        rule_chain=["rule_1", "rule_2", "rule_3"],
        evidence_nodes=["node_1", "node_2"],
        contradiction_branches=["branch_1"],
        symbolic_trace_hash="abc123def456",
        governance_scope_id="scope-001",
    )


@pytest.fixture
def provenance_with_attestation(
    provenance_attestation: ProvenanceAttestation, inference_provenance: InferenceProvenance
) -> ProvenanceWithAttestation:
    """Create ProvenanceWithAttestation instance"""
    return ProvenanceWithAttestation.create(
        source="test_source",
        correlation_id="test-001",
        author="system",
        governance_scope_id="scope-001",
        runtime_attestation_id="attest-001",
        inference_provenance=inference_provenance,
    )


# ============================================================================
# FIXTURES: ProvenanceChain
# ============================================================================


@pytest.fixture
def provenance_chain() -> ProvenanceChain:
    """Create ProvenanceChain instance"""
    return ProvenanceChain()


# ============================================================================
# FIXTURES: Correlation IDs
# ============================================================================


@pytest.fixture
def correlation_id_1() -> str:
    """First correlation ID"""
    return "req-001"


@pytest.fixture
def correlation_id_2() -> str:
    """Second correlation ID"""
    return "req-002"


@pytest.fixture
def correlation_id_3() -> str:
    """Third correlation ID"""
    return "req-003"


# ============================================================================
# FIXTURES: Timestamps
# ============================================================================


@pytest.fixture
def current_timestamp() -> str:
    """Current timestamp in ISO format"""
    return datetime.now(UTC).isoformat()


@pytest.fixture
def past_timestamp() -> str:
    """Past timestamp in ISO format"""
    return datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC).isoformat()
