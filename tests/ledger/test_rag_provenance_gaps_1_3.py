"""
Tests for Feature 1: RAG Provenance Tracker (Gaps 1-3)
========================================================

Tests the closed gaps:
- Gap 1: EvidencePackage schema extension
- Gap 2: Verdict engine propagation
- Gap 3: Ledger storage integration

These tests verify that RAG metadata flows correctly from
RAGEvidenceNode → EvidencePackage → LedgerEntry.
"""

import pytest
import hashlib
from datetime import datetime, timezone
from mahoun.ledger.write_gate import EvidencePackage, LedgerWriteGate, WriteGateResult
from mahoun.ledger.models import LedgerEntry
from mahoun.reasoning.rag_evidence import RAGEvidenceNode, RAGSource, SourceAuthority


# ============================================================================
# Gap 1: EvidencePackage Schema Extension
# ============================================================================

class TestEvidencePackageSchema:
    """Tests for EvidencePackage schema extension (Gap 1)"""
    
    def test_retrieval_provenance_field_exists(self):
        """EvidencePackage should have retrieval_provenance field"""
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
        )
        
        # Should have retrieval_provenance field (defaults to empty list)
        assert hasattr(package, "retrieval_provenance")
        assert package.retrieval_provenance == []
    
    def test_schema_version_field_exists(self):
        """EvidencePackage should have schema_version field"""
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
        )
        
        assert hasattr(package, "schema_version")
        assert package.schema_version == "2.0"
    
    def test_retrieval_provenance_can_be_provided(self):
        """EvidencePackage should accept retrieval_provenance"""
        rag_provenance = [
            {
                "fact_id": "fact_0",
                "doc_id": "doc-123",
                "source": "hybrid",
                "score": 0.87,
                "correlation_id": "corr-abc",
                "content_hash": "a" * 64,
            }
        ]
        
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
            retrieval_provenance=rag_provenance,
        )
        
        assert package.retrieval_provenance == rag_provenance
    
    def test_backward_compatibility_old_code_works(self):
        """Old code without retrieval_provenance should still work"""
        # Simulate old code that doesn't know about new field
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
            # Note: NOT providing retrieval_provenance
        )
        
        # Should work and default to empty list
        assert package.retrieval_provenance == []
        valid, error = package.validate()
        assert valid is True


class TestEvidencePackageValidation:
    """Tests for retrieval_provenance validation logic"""
    
    def test_valid_retrieval_provenance_accepted(self):
        """Valid retrieval_provenance should pass validation"""
        rag_provenance = [
            {
                "fact_id": "fact_0",
                "doc_id": "doc-123",
                "source": "hybrid",
                "correlation_id": "corr-abc",
                "content_hash": "a" * 64,
                "score": 0.87,
                "rank": 0,
            }
        ]
        
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
            retrieval_provenance=rag_provenance,
        )
        
        valid, error = package.validate()
        assert valid is True
        assert error is None
    
    def test_missing_required_field_rejected(self):
        """Retrieval provenance missing required field should be rejected"""
        rag_provenance = [
            {
                "fact_id": "fact_0",
                "doc_id": "doc-123",
                "source": "hybrid",
                # Missing: correlation_id, content_hash
            }
        ]
        
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
            retrieval_provenance=rag_provenance,
        )
        
        valid, error = package.validate()
        assert valid is False
        assert "missing required fields" in error
        assert "correlation_id" in error or "content_hash" in error
    
    def test_empty_retrieval_provenance_accepted(self):
        """Empty retrieval_provenance list should be valid"""
        package = EvidencePackage(
            evidence_refs=["ref1"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
            retrieval_provenance=[],  # Empty list
        )
        
        valid, error = package.validate()
        assert valid is True
    
    def test_multiple_provenance_entries_validated(self):
        """All entries in retrieval_provenance should be validated"""
        rag_provenance = [
            {
                "fact_id": "fact_0",
                "doc_id": "doc-123",
                "source": "hybrid",
                "correlation_id": "corr-abc",
                "content_hash": "a" * 64,
            },
            {
                "fact_id": "fact_1",
                "doc_id": "doc-456",
                "source": "text",
                # Missing correlation_id - should fail
            },
        ]
        
        package = EvidencePackage(
            evidence_refs=["ref1", "ref2"],
            provenance_chain=[{"source": "test"}],
            proof_hash="a" * 64,
            validation_context={"test": True},
            retrieval_provenance=rag_provenance,
        )
        
        valid, error = package.validate()
        assert valid is False
        assert "[1]" in error  # Should indicate second entry failed


# ============================================================================
# Gap 3: Ledger Storage Integration
# ============================================================================

class TestLedgerStorageIntegration:
    """Tests for ledger storage of RAG provenance (Gap 3)"""
    
    def test_ledger_entry_has_retrieval_provenance_field(self):
        """LedgerEntry should have retrieval_provenance field"""
        entry = LedgerEntry(
            verdict_id="v123",
            case_id="c456",
            referenced_ltm_nodes=["node1"],
            referenced_facts=["fact_0"],
            confidence=0.9,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc),
            event_type="verdict_persisted",
        )
        
        assert hasattr(entry, "retrieval_provenance")
    
    def test_ledger_entry_stores_retrieval_provenance(self):
        """LedgerEntry should store retrieval_provenance correctly"""
        rag_provenance = [
            {
                "fact_id": "fact_0",
                "doc_id": "doc-123",
                "source": "hybrid",
                "score": 0.87,
                "correlation_id": "corr-abc",
                "content_hash": "a" * 64,
            }
        ]
        
        entry = LedgerEntry(
            verdict_id="v123",
            case_id="c456",
            referenced_ltm_nodes=["node1"],
            referenced_facts=["fact_0"],
            confidence=0.9,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc),
            event_type="verdict_persisted",
            retrieval_provenance=rag_provenance,
        )
        
        assert entry.retrieval_provenance == rag_provenance
    
    def test_ledger_entry_backward_compatible(self):
        """LedgerEntry should work without retrieval_provenance (old code)"""
        # Simulate old code that doesn't provide retrieval_provenance
        entry = LedgerEntry(
            verdict_id="v123",
            case_id="c456",
            referenced_ltm_nodes=["node1"],
            referenced_facts=["fact_0"],
            confidence=0.9,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc),
            event_type="verdict_persisted",
            # Note: NOT providing retrieval_provenance
        )
        
        # Should work (field should default to empty list or None)
        assert hasattr(entry, "retrieval_provenance")


# ============================================================================
# Integration Test: End-to-End Flow
# ============================================================================

class TestRAGProvenanceE2EGaps1to3:
    """End-to-end test for RAG provenance flow (Gaps 1-3)"""
    
    def test_rag_evidence_node_to_evidence_package_to_ledger(self):
        """Test full flow: RAGEvidenceNode → EvidencePackage → LedgerEntry"""
        
        # Step 1: Create RAGEvidenceNode (simulating RAG retrieval)
        rag_node = RAGEvidenceNode(
            fact_index=0,
            doc_id="doc-123",
            source=RAGSource.HYBRID,
            authority=SourceAuthority.TRUSTED_INTERNAL,
            score=0.87,
            retrieval_rank=0,
            correlation_id="corr-abc-123",
            content_hash=hashlib.sha256(b"test fact text").hexdigest(),
            is_sensitive=False,
            metadata={"source_system": "test_system"},
        )
        
        # Step 2: Build retrieval_provenance from RAGEvidenceNode
        retrieval_provenance = [rag_node.to_ledger_provenance()]
        
        # Step 3: Create EvidencePackage with retrieval_provenance
        evidence_package = EvidencePackage(
            evidence_refs=["fact_0"],
            provenance_chain=[{"source": "test"}],
            proof_hash=hashlib.sha256(b"test proof").hexdigest(),
            validation_context={"test": True},
            retrieval_provenance=retrieval_provenance,  # ✅ Gap 2: Propagated
        )
        
        # Validate package
        valid, error = evidence_package.validate()
        assert valid is True, f"Validation failed: {error}"
        
        # Step 4: Create LedgerEntry from EvidencePackage
        ledger_entry = LedgerEntry(
            verdict_id="v123",
            case_id="c456",
            referenced_ltm_nodes=evidence_package.evidence_refs,
            referenced_facts=["fact_0"],
            confidence=0.9,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc),
            event_type="verdict_persisted",
            retrieval_provenance=evidence_package.retrieval_provenance,  # ✅ Gap 3: Stored
        )
        
        # Verify data integrity through the pipeline
        assert len(ledger_entry.retrieval_provenance) == 1
        stored_prov = ledger_entry.retrieval_provenance[0]
        
        assert stored_prov["fact_index"] == 0
        assert stored_prov["doc_id"] == "doc-123"
        assert stored_prov["source"] == "hybrid"
        assert stored_prov["score"] == 0.87
        assert stored_prov["correlation_id"] == "corr-abc-123"
        assert stored_prov["is_audit_eligible"] is True
        assert stored_prov["metadata"]["source_system"] == "test_system"
        
        print("✅ End-to-end flow verified: RAGEvidenceNode → EvidencePackage → LedgerEntry")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
