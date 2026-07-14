"""
✅ GAP 4 INTEGRATION TESTS: RAG Provenance → Proof Tree

Tests the integration of existing infrastructure:
- ProvenanceMetadata (cryptographic fields)
- MerkleTree (proof generation)
- RAGEvidenceNode (evidence wrapping)

NO NEW MODULES - pure integration testing of existing infrastructure.
"""

import pytest


def test_merkle_proof_verification():
    """
    ✅ GAP 4: Test Merkle proof verification for RAG evidence.
    
    Verifies that generated Merkle proofs are valid.
    
    NOTE: MerkleTree sorts leaves for determinism, so we must use sorted index.
    """
    from mahoun.crypto.merkle_tree import MerkleTree
    
    # Create Merkle tree with RAG evidence (using content, not hashes)
    tree = MerkleTree()
    evidence_content = [
        "Article 219: Contract requires 30 days notice",
        "Article 220: Penalty is 10%",
        "Article 221: Both parties must agree",
    ]
    
    for content in evidence_content:
        tree.add(content)
    
    root = tree.get_root()
    
    # IMPORTANT: MerkleTree sorts leaves internally for determinism
    # So we need to find the sorted index of our evidence
    sorted_leaves = sorted(tree.leaves)
    
    # Find which leaf we want to prove (first evidence after sorting)
    leaf_hash_to_prove = tree.leaves[0]  # First leaf we added
    sorted_index = sorted_leaves.index(leaf_hash_to_prove)
    
    # Get proof for the sorted index
    proof = tree.get_proof(sorted_index)
    
    # Verify proof using original content
    is_valid = tree.verify_proof(evidence_content[0], proof, root)
    assert is_valid
    
    # Verify tampered evidence fails
    tampered_content = "FAKE ARTICLE: This is not real"
    is_valid_tampered = tree.verify_proof(tampered_content, proof, root)
    assert not is_valid_tampered


def test_provenance_metadata_cryptographic_fields():
    """
    ✅ GAP 4: Test ProvenanceMetadata cryptographic fields.
    
    Verifies that ProvenanceMetadata.create() generates all required fields.
    """
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    
    prov = ProvenanceMetadata.create(
        source="rag_retrieval_test",
        correlation_id="test_corr_789",
        author="test_author",
        governance_scope_id="scope_test_123",
        runtime_attestation_id="attest_test_456",
        document_id="doc_test_789",
    )
    
    # Verify all cryptographic fields present
    assert prov.provenance_hash is not None
    assert len(prov.provenance_hash) == 64  # SHA-256
    assert prov.provenance_signature is not None
    assert len(prov.provenance_signature) == 64  # SHA-256
    assert prov.governance_scope_id == "scope_test_123"
    assert prov.runtime_attestation_id == "attest_test_456"
    
    # Verify serialization
    prov_dict = prov.to_dict()
    assert "provenance_hash" in prov_dict
    assert "provenance_signature" in prov_dict
    assert "governance_scope_id" in prov_dict
    assert "runtime_attestation_id" in prov_dict


def test_rag_evidence_node_creation():
    """
    ✅ GAP 4: Test RAGEvidenceNode creation with all fields.
    
    Verifies that RAGEvidenceNode can be created with proper validation.
    """
    from mahoun.reasoning.rag_evidence import RAGEvidenceNode, RAGSource, SourceAuthority
    
    node = RAGEvidenceNode(
        fact_index=0,
        doc_id="test_doc_123",
        source=RAGSource.HYBRID,
        authority=SourceAuthority.TRUSTED_INTERNAL,
        score=0.85,
        retrieval_rank=0,
        correlation_id="test_corr_123",
        content_hash="a" * 64,  # Valid SHA-256
        is_sensitive=False,
        metadata={"test": "value"},
    )
    
    # Verify fields
    assert node.fact_index == 0
    assert node.doc_id == "test_doc_123"
    assert node.score == 0.85
    assert node.is_high_confidence()
    assert node.is_audit_eligible()
    
    # Verify serialization
    ledger_prov = node.to_ledger_provenance()
    assert "fact_index" in ledger_prov
    assert "content_hash" in ledger_prov
    assert "stable_id" in ledger_prov
    assert ledger_prov["is_audit_eligible"] == True


def test_integration_flow_create_rag_proof_section():
    """
    ✅ GAP 4: Test _create_rag_proof_tree_section integration.
    
    Verifies the complete flow without running full verdict engine.
    """
    from mahoun.reasoning.rag_evidence import RAGEvidenceNode, RAGSource, SourceAuthority
    from mahoun.crypto.merkle_tree import MerkleTree
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    
    # Create RAG evidence map (simulates what verdict engine does)
    rag_evidence_map = {
        0: RAGEvidenceNode(
            fact_index=0,
            doc_id="doc_1",
            source=RAGSource.HYBRID,
            authority=SourceAuthority.TRUSTED_INTERNAL,
            score=0.85,
            retrieval_rank=0,
            correlation_id="test_123",
            content_hash="a" * 64,
        ),
        1: RAGEvidenceNode(
            fact_index=1,
            doc_id="doc_2",
            source=RAGSource.GRAPH,
            authority=SourceAuthority.TRUSTED_PARTNER,
            score=0.90,
            retrieval_rank=1,
            correlation_id="test_123",
            content_hash="b" * 64,
        ),
    }
    
    # Build Merkle tree (simulates _create_rag_proof_tree_section)
    merkle_tree = MerkleTree()
    evidence_items = []
    
    for idx, rag_node in sorted(rag_evidence_map.items()):
        # Add to Merkle tree
        merkle_tree.add(rag_node.content_hash)
        
        # Create provenance
        crypto_prov = ProvenanceMetadata.create(
            source=f"rag_retrieval_{rag_node.source.value}",
            correlation_id=rag_node.correlation_id,
            author="rag_engine",
            governance_scope_id=rag_node.correlation_id,
            runtime_attestation_id=f"rag_{rag_node.stable_id[:16]}",
            document_id=rag_node.doc_id,
        )
        
        # Get proof
        merkle_proof = merkle_tree.get_proof(idx)
        
        evidence_items.append({
            "fact_index": rag_node.fact_index,
            "doc_id": rag_node.doc_id,
            "cryptographic_provenance": crypto_prov.to_dict(),
            "merkle_proof": merkle_proof,
        })
    
    # Verify result structure
    assert len(evidence_items) == 2
    merkle_root = merkle_tree.get_root()
    assert len(merkle_root) == 64
    
    # Verify each item has required fields
    for item in evidence_items:
        assert "fact_index" in item
        assert "doc_id" in item
        assert "cryptographic_provenance" in item
        assert "merkle_proof" in item
        
        crypto_prov = item["cryptographic_provenance"]
        assert "provenance_hash" in crypto_prov
        assert "governance_scope_id" in crypto_prov


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
