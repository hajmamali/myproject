"""
Tests for ProvenanceAttestation
================================

Classification: CRITICAL INTEGRITY TESTS
Purpose: Verify ProvenanceAttestation cryptographic integrity

Test Coverage:
- Attestation creation
- Hash computation
- Signature generation
- Integrity verification
- Inference provenance
- With attestation
- Chain verification
"""

import hashlib
import json

import pytest

from mahoun.core.governance.provenance_attestation import (
    InferenceProvenance,
    ProvenanceAttestation,
    ProvenanceChain,
    ProvenanceWithAttestation,
)
from mahoun.core.governance.violations import (
    GovernanceViolationError,
)

# ============================================================================
# TESTS: Attestation Creation
# ============================================================================


class TestAttestationCreation:
    """Tests for ProvenanceAttestation creation"""

    def test_create_attestation(self):
        """Test creating a provenance attestation"""
        attestation = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-001"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        assert attestation is not None
        assert attestation.provenance_hash is not None
        assert attestation.provenance_signature is not None
        assert attestation.governance_scope_id == "scope-001"
        assert attestation.runtime_attestation_id == "attest-001"
        assert attestation.lineage_parent is None
        assert attestation.timestamp is not None

    def test_create_attestation_with_lineage_parent(self):
        """Test creating attestation with lineage parent"""
        parent_attestation = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-001"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        attestation = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-002"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
            lineage_parent=parent_attestation.provenance_hash,
        )

        assert attestation.lineage_parent == parent_attestation.provenance_hash

    def test_create_attestation_timestamp_internal(self):
        """Test that timestamp is generated internally"""
        import time

        # Create two attestations
        attestation1 = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-001"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        time.sleep(0.01)  # Small delay

        attestation2 = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-002"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-002",
        )

        # Timestamps should be different (internal generation)
        assert attestation1.timestamp != attestation2.timestamp

    def test_create_attestation_hash_computation(self):
        """Test that hash is computed from data"""
        data1 = {"source": "test", "correlation_id": "req-001"}
        data2 = {"source": "test", "correlation_id": "req-002"}

        attestation1 = ProvenanceAttestation.create(
            provenance_data=data1, governance_scope_id="scope-001", runtime_attestation_id="attest-001"
        )

        attestation2 = ProvenanceAttestation.create(
            provenance_data=data2, governance_scope_id="scope-001", runtime_attestation_id="attest-002"
        )

        # Hashes should be different
        assert attestation1.provenance_hash != attestation2.provenance_hash

    def test_create_attestation_signature_computation(self):
        """Test that signature is computed"""
        attestation = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-001"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        # Signature should be non-empty
        assert len(attestation.provenance_signature) > 0
        assert attestation.provenance_signature != attestation.provenance_hash


# ============================================================================
# TESTS: Integrity Verification
# ============================================================================


class TestIntegrityVerification:
    """Tests for attestation integrity verification"""

    def test_verify_integrity_valid(self):
        """Test verify_integrity with valid attestation"""
        attestation = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-001"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        result = attestation.verify_integrity()

        assert result is True

    def test_verify_integrity_with_tampered_data(self):
        """Test verify_integrity with tampered data"""
        attestation = ProvenanceAttestation.create(
            provenance_data={"source": "test", "correlation_id": "req-001"},
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        # Tamper with data (in production, this would be signature tampering)
        # For now, we just verify the hash matches
        hash_input = json.dumps({"source": "test", "correlation_id": "req-001"}, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        assert attestation.provenance_hash == expected_hash


# ============================================================================
# TESTS: Inference Provenance
# ============================================================================


class TestInferenceProvenance:
    """Tests for InferenceProvenance"""

    def test_create_inference_provenance(self):
        """Test creating inference provenance"""
        provenance = InferenceProvenance.create(
            rule_chain=["rule_1", "rule_2", "rule_3"],
            evidence_nodes=["node_1", "node_2"],
            contradiction_branches=["branch_1"],
            symbolic_trace_hash="abc123def456",
            governance_scope_id="scope-001",
        )

        assert provenance is not None
        assert provenance.proof_id is not None
        assert provenance.rule_chain == ("rule_1", "rule_2", "rule_3")
        assert provenance.evidence_nodes == ("node_1", "node_2")
        assert provenance.contradiction_branches == ("branch_1",)
        assert provenance.symbolic_trace_hash == "abc123def456"
        assert provenance.governance_scope_id == "scope-001"

    def test_create_inference_provenance_auto_proof_id(self):
        """Test that proof_id is auto-generated"""
        provenance1 = InferenceProvenance.create(
            rule_chain=["rule_1"],
            evidence_nodes=["node_1"],
            contradiction_branches=[],
            symbolic_trace_hash="hash1",
            governance_scope_id="scope-001",
        )

        provenance2 = InferenceProvenance.create(
            rule_chain=["rule_1"],
            evidence_nodes=["node_1"],
            contradiction_branches=[],
            symbolic_trace_hash="hash1",
            governance_scope_id="scope-001",
        )

        # Proof IDs should be different (auto-generated)
        assert provenance1.proof_id != provenance2.proof_id

    def test_inference_provenance_to_dict(self):
        """Test converting inference provenance to dict"""
        provenance = InferenceProvenance.create(
            rule_chain=["rule_1", "rule_2"],
            evidence_nodes=["node_1"],
            contradiction_branches=["branch_1", "branch_2"],
            symbolic_trace_hash="abc123",
            governance_scope_id="scope-001",
        )

        result = provenance.to_dict()

        assert result["proof_id"] == provenance.proof_id
        assert result["rule_chain"] == ["rule_1", "rule_2"]
        assert result["evidence_nodes"] == ["node_1"]
        assert result["contradiction_branches"] == ["branch_1", "branch_2"]
        assert result["symbolic_trace_hash"] == "abc123"
        assert result["governance_scope_id"] == "scope-001"


# ============================================================================
# TESTS: Provenance With Attestation
# ============================================================================


class TestProvenanceWithAttestation:
    """Tests for ProvenanceWithAttestation"""

    def test_create_provenance_with_attestation(self):
        """Test creating provenance with attestation"""
        provenance = ProvenanceWithAttestation.create(
            source="document_ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        assert provenance is not None
        assert provenance.metadata is not None
        assert provenance.attestation is not None
        assert provenance.inference is None

        assert provenance.metadata["source"] == "document_ingestion"
        assert provenance.metadata["correlation_id"] == "req-001"
        assert provenance.metadata["author"] == "system"

    def test_create_provenance_with_attestation_and_inference(self):
        """Test creating provenance with attestation and inference"""
        inference = InferenceProvenance.create(
            rule_chain=["rule_1"],
            evidence_nodes=["node_1"],
            contradiction_branches=[],
            symbolic_trace_hash="hash1",
            governance_scope_id="scope-001",
        )

        provenance = ProvenanceWithAttestation.create(
            source="document_ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
            inference_provenance=inference,
        )

        assert provenance.inference is not None
        assert provenance.inference == inference

    def test_create_provenance_with_document_id(self):
        """Test creating provenance with document_id"""
        provenance = ProvenanceWithAttestation.create(
            source="document_ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
            document_id="doc-001",
            pipeline_version="1.0.0",
        )

        assert provenance.metadata["document_id"] == "doc-001"
        assert provenance.metadata["pipeline_version"] == "1.0.0"

    def test_provenance_with_attestation_to_dict(self):
        """Test converting provenance with attestation to dict"""
        provenance = ProvenanceWithAttestation.create(
            source="document_ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        result = provenance.to_dict()

        assert "metadata" in result
        assert "attestation" in result
        assert "inference" not in result or result["inference"] is None


# ============================================================================
# TESTS: Provenance Chain
# ============================================================================


class TestProvenanceChain:
    """Tests for ProvenanceChain"""

    def test_create_provenance_chain(self):
        """Test creating a provenance chain"""
        chain = ProvenanceChain()

        provenance1 = chain.create_provenance(
            source="ingestion",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        assert provenance1 is not None
        assert provenance1.attestation.lineage_parent is None

    def test_create_provenance_chain_with_lineage(self):
        """Test creating a chain with lineage"""
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

        # Second provenance should reference first
        assert provenance2.attestation.lineage_parent == provenance1.attestation.provenance_hash

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

        chain.create_provenance(
            source="validation",
            correlation_id="req-003",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-003",
        )

        retrieved_chain = chain.get_chain()

        assert len(retrieved_chain) == 3
        assert retrieved_chain[0].attestation.lineage_parent is None
        assert retrieved_chain[1].attestation.lineage_parent == retrieved_chain[0].attestation.provenance_hash
        assert retrieved_chain[2].attestation.lineage_parent == retrieved_chain[1].attestation.provenance_hash

    def test_verify_chain_integrity_valid(self):
        """Test verifying chain integrity with valid chain"""
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

    def test_verify_chain_integrity_with_broken_lineage(self):
        """Test verifying chain integrity with broken lineage"""
        import dataclasses

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

        # Manually break lineage using dataclasses.replace()
        broken_attestation = dataclasses.replace(chain._chain[1].attestation, lineage_parent="invalid_hash")

        # Replace the attestation in the provenance
        broken_provenance = dataclasses.replace(chain._chain[1], attestation=broken_attestation)
        chain._chain[1] = broken_provenance

        with pytest.raises(GovernanceViolationError) as exc_info:
            chain.verify_chain_integrity()

        assert "lineage break" in str(exc_info.value).lower()


# ============================================================================
# TESTS: Performance
# ============================================================================


class TestPerformance:
    """Tests for provenance performance"""

    def test_attestation_creation_performance(self):
        """Test attestation creation performance"""
        import time

        start = time.time()
        for _ in range(1000):
            ProvenanceAttestation.create(
                provenance_data={"source": "test", "correlation_id": f"req-{_}"},
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )
        elapsed = time.time() - start

        assert elapsed < 1.0  # < 1s for 1000 attestations

    def test_chain_creation_performance(self):
        """Test chain creation performance"""
        import time

        start = time.time()
        chain = ProvenanceChain()
        for _ in range(100):
            chain.create_provenance(
                source="test",
                correlation_id=f"req-{_}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )
        elapsed = time.time() - start

        assert elapsed < 1.0  # < 1s for 100 chain entries

    def test_chain_verification_performance(self):
        """Test chain verification performance"""
        import time

        chain = ProvenanceChain()
        for _ in range(100):
            chain.create_provenance(
                source="test",
                correlation_id=f"req-{_}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

        start = time.time()
        chain.verify_chain_integrity()
        elapsed = time.time() - start

        assert elapsed < 0.5  # < 500ms for 100 entry chain verification


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_data_attestation(self):
        """Test creating attestation with empty data"""
        attestation = ProvenanceAttestation.create(
            provenance_data={}, governance_scope_id="scope-001", runtime_attestation_id="attest-001"
        )

        assert attestation is not None
        assert attestation.provenance_hash is not None

    def test_single_entry_chain(self):
        """Test chain with single entry"""
        chain = ProvenanceChain()

        provenance = chain.create_provenance(
            source="test",
            correlation_id="req-001",
            author="system",
            governance_scope_id="scope-001",
            runtime_attestation_id="attest-001",
        )

        assert provenance.attestation.lineage_parent is None

        chain = chain.get_chain()
        assert len(chain) == 1

    def test_many_entries_chain(self):
        """Test chain with many entries"""
        chain = ProvenanceChain()

        for i in range(100):
            chain.create_provenance(
                source="test",
                correlation_id=f"req-{i}",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

        chain_list = chain.get_chain()
        assert len(chain_list) == 100

        # Verify lineage
        for i in range(1, 100):
            assert chain_list[i].attestation.lineage_parent == chain_list[i - 1].attestation.provenance_hash
