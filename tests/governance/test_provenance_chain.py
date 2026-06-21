"""
Tests for ProvenanceChain
==========================

Classification: CRITICAL LINEAGE TESTS
Purpose: Verify ProvenanceChain lineage tracking

Test Coverage:
- Chain creation
- Lineage tracking
- Chain verification
- Integrity validation
"""

import pytest

from mahoun.core.governance.provenance_attestation import (
    InferenceProvenance,
    ProvenanceChain,
    ProvenanceWithAttestation,
)
from mahoun.core.governance.violations import GovernanceViolationError

# ============================================================================
# TESTS: Chain Creation
# ============================================================================


class TestChainCreation:
    """Tests for ProvenanceChain creation"""

    def test_create_chain(self):
        """Test creating a provenance chain"""
        chain = ProvenanceChain()

        assert chain is not None
        assert chain._current_attestation_id is None
        assert chain._current_lineage_parent is None
        assert len(chain._chain) == 0

    def test_create_provenance_first_entry(self):
        """Test creating first entry in chain"""
        chain = ProvenanceChain()

        provenance = chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        assert provenance is not None
        assert provenance.attestation.lineage_parent is None
        assert len(chain._chain) == 1

    def test_create_provenance_with_inference(self):
        """Test creating provenance with inference"""
        chain = ProvenanceChain()

        inference = InferenceProvenance.create(
            rule_chain=["rule_1"],
            evidence_nodes=["node_1"],
            contradiction_branches=[],
            symbolic_trace_hash="hash1",
            governance_scope_id="scope-001",
        )

        provenance = chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
            inference_provenance=inference,
        )

        assert provenance.inference is not None
        assert provenance.inference == inference


# ============================================================================
# TESTS: Lineage Tracking
# ============================================================================


class TestLineageTracking:
    """Tests for lineage tracking"""

    def test_lineage_parent_auto_set(self):
        """Test that lineage_parent is automatically set"""
        chain = ProvenanceChain()

        provenance1 = chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        provenance2 = chain.create_provenance(
            source="processing",
            correlation_id="req-002",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
        )

        provenance3 = chain.create_provenance(
            source="validation",
            correlation_id="req-003",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-003",
        )

        # Verify lineage chain
        assert provenance1.attestation.lineage_parent is None
        assert provenance2.attestation.lineage_parent == provenance1.attestation.provenance_hash
        assert provenance3.attestation.lineage_parent == provenance2.attestation.provenance_hash

    def test_lineage_chain_length(self):
        """Test that lineage chain grows correctly"""
        chain = ProvenanceChain()

        for i in range(10):
            chain.create_provenance(
                source=f"stage_{i}",
                correlation_id=f"req-{i}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

        chain_list = chain.get_chain()
        assert len(chain_list) == 10

        # Verify lineage
        for i in range(1, 10):
            assert chain_list[i].attestation.lineage_parent == chain_list[i - 1].attestation.provenance_hash

    def test_lineage_with_custom_parent(self):
        """Test creating provenance with custom lineage parent"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        # Create with custom parent
        provenance2 = ProvenanceWithAttestation.create(
            source="processing",
            correlation_id="req-002",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
            lineage_parent="custom_parent_hash",
        )

        assert provenance2.attestation.lineage_parent == "custom_parent_hash"


# ============================================================================
# TESTS: Chain Verification
# ============================================================================


class TestChainVerification:
    """Tests for chain verification"""

    def test_verify_chain_valid(self):
        """Test verifying valid chain"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        chain.create_provenance(
            source="processing",
            correlation_id="req-002",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
        )

        result = chain.verify_chain_integrity()

        assert result is True

    def test_verify_chain_broken_lineage(self):
        """Test verifying chain with broken lineage"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        chain.create_provenance(
            source="processing",
            correlation_id="req-002",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
        )

        # CRITICAL: Break lineage using dataclasses.replace()
        # Cannot directly modify frozen dataclass - must create new instance
        import dataclasses

        broken_attestation = dataclasses.replace(chain._chain[1].attestation, lineage_parent="invalid_hash")

        # Replace attestation in chain
        broken_provenance = dataclasses.replace(chain._chain[1], attestation=broken_attestation)
        chain._chain[1] = broken_provenance

        with pytest.raises(GovernanceViolationError) as exc_info:
            chain.verify_chain_integrity()

        assert "lineage break" in str(exc_info.value).lower()

    def test_verify_chain_empty(self):
        """Test verifying empty chain"""
        chain = ProvenanceChain()

        result = chain.verify_chain_integrity()

        assert result is True  # Empty chain is valid

    def test_verify_chain_single_entry(self):
        """Test verifying single entry chain"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        result = chain.verify_chain_integrity()

        assert result is True


# ============================================================================
# TESTS: Chain Retrieval
# ============================================================================


class TestChainRetrieval:
    """Tests for chain retrieval"""

    def test_get_chain(self):
        """Test getting full chain"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        chain.create_provenance(
            source="processing",
            correlation_id="req-002",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
        )

        chain_list = chain.get_chain()

        assert len(chain_list) == 2
        assert chain_list[0].attestation.lineage_parent is None
        assert chain_list[1].attestation.lineage_parent == chain_list[0].attestation.provenance_hash

    def test_get_chain_is_copy(self):
        """Test that get_chain returns a copy"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        chain_list1 = chain.get_chain()
        chain_list2 = chain.get_chain()

        # Should be different objects
        assert chain_list1 is not chain_list2

        # But should have same content
        assert len(chain_list1) == len(chain_list2)
        assert chain_list1[0].attestation.provenance_hash == chain_list2[0].attestation.provenance_hash

    def test_get_chain_empty(self):
        """Test getting empty chain"""
        chain = ProvenanceChain()

        chain_list = chain.get_chain()

        assert len(chain_list) == 0


# ============================================================================
# TESTS: Performance
# ============================================================================


class TestPerformance:
    """Tests for ProvenanceChain performance"""

    def test_chain_creation_performance(self):
        """Test chain creation performance"""
        import time

        chain = ProvenanceChain()

        start = time.time()
        for i in range(1000):
            chain.create_provenance(
                source=f"stage_{i}",
                correlation_id=f"req-{i}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )
        elapsed = time.time() - start

        assert elapsed < 2.0  # < 2s for 1000 entries

    def test_chain_verification_performance(self):
        """Test chain verification performance"""
        import time

        chain = ProvenanceChain()
        for i in range(1000):
            chain.create_provenance(
                source=f"stage_{i}",
                correlation_id=f"req-{i}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

        start = time.time()
        chain.verify_chain_integrity()
        elapsed = time.time() - start

        assert elapsed < 1.0  # < 1s for 1000 entry chain verification

    def test_large_chain_verification(self):
        """Test verification of large chain"""
        chain = ProvenanceChain()

        for i in range(10000):
            chain.create_provenance(
                source=f"stage_{i}",
                correlation_id=f"req-{i}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

        # Should complete without error
        result = chain.verify_chain_integrity()
        assert result is True


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases"""

    def test_single_entry_chain_verification(self):
        """Test verification of single entry chain"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        result = chain.verify_chain_integrity()
        assert result is True

    def test_chain_with_inference(self):
        """Test chain with inference provenance"""
        chain = ProvenanceChain()

        inference = InferenceProvenance.create(
            rule_chain=["rule_1", "rule_2"],
            evidence_nodes=["node_1", "node_2"],
            contradiction_branches=["branch_1"],
            symbolic_trace_hash="hash1",
            governance_scope_id="scope-001",
        )

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
            inference_provenance=inference,
        )

        chain_list = chain.get_chain()
        assert chain_list[0].inference is not None
        assert chain_list[0].inference == inference

    def test_chain_with_document_id(self):
        """Test chain with document_id"""
        chain = ProvenanceChain()

        chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
            document_id="doc-001",
            pipeline_version="1.0.0",
        )

        chain_list = chain.get_chain()
        assert chain_list[0].metadata["document_id"] == "doc-001"
        assert chain_list[0].metadata["pipeline_version"] == "1.0.0"

    def test_chain_lineage_continuity(self):
        """Test that lineage is continuous"""
        chain = ProvenanceChain()

        for i in range(100):
            chain.create_provenance(
                source=f"stage_{i}",
                correlation_id=f"req-{i}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

        chain_list = chain.get_chain()

        # Verify lineage continuity
        for i in range(1, 100):
            current = chain_list[i]
            parent = chain_list[i - 1]

            assert current.attestation.lineage_parent == parent.attestation.provenance_hash

        # Verify chain integrity
        result = chain.verify_chain_integrity()
        assert result is True
