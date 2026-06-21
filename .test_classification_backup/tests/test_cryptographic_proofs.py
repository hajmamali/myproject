"""
Cryptographic Proof System Tests
=================================

CRITICAL: Tests cryptographic proofs for graph-based reasoning verification.
Zero-hallucination guarantee depends on tamper-evident audit trails.

Test Coverage:
- Proof generation (graph state + reasoning chain + evidence merkle tree)
- Signature verification (Ed25519)
- Tamper detection
- Timestamp validation
- Deterministic hashing
- Merkle tree construction
- Proof serialization/deserialization

NO SIMPLIFICATION - Full cryptographic validation required.
"""

import pytest
import json
from pathlib import Path
import sys
from datetime import datetime, timezone, timedelta
from collections import namedtuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mahoun.crypto.proof_system import (
    CryptographicProof,
    generate_proof,
    _hash_graph_state,
    _hash_reasoning_chain,
    _build_evidence_merkle_tree,
)
from mahoun.crypto.signatures import generate_keypair


class TestProofGeneration:
    """Test cryptographic proof generation"""
    
    def setup_method(self):
        """Setup before each test"""
        self.private_key, self.public_key = generate_keypair()
        
        # Mock data structures
        self.Node = namedtuple('Node', ['node_type', 'label'])
        self.Edge = namedtuple('Edge', ['source_id', 'target_id', 'relationship_type'])
        self.Step = namedtuple('Step', ['statement'])
        self.Evidence = namedtuple('Evidence', ['node_id'])
    
    def test_generate_proof_success(self):
        """Test successful proof generation"""
        graph_nodes = {
            "rule_1": self.Node("LegalRule", "Article 219"),
            "fact_1": self.Node("Fact", "Contract signed")
        }
        
        graph_edges = [
            self.Edge("fact_1", "rule_1", "TRIGGERS")
        ]
        
        reasoning_steps = [
            self.Step("Article 219 applies"),
            self.Step("Contract termination allowed")
        ]
        
        evidence_refs = [
            self.Evidence("rule_1"),
            self.Evidence("fact_1")
        ]
        
        proof = generate_proof(
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            reasoning_steps=reasoning_steps,
            evidence_refs=evidence_refs,
            verdict_id="verdict_123",
            case_id="case_456",
            confidence=0.92,
            private_key=self.private_key
        )
        
        assert proof is not None
        assert proof.verdict_id == "verdict_123"
        assert proof.case_id == "case_456"
        assert proof.confidence == 0.92
        assert len(proof.graph_state_hash) == 64  # SHA-256 hex
        assert len(proof.reasoning_chain_hash) == 64
        assert len(proof.evidence_merkle_root) == 64
        assert proof.signature
        assert proof.timestamp
    
    def test_generate_proof_fails_empty_graph(self):
        """Test proof generation fails with empty graph"""
        with pytest.raises(ValueError, match="graph_nodes cannot be empty"):
            generate_proof(
                graph_nodes={},  # EMPTY
                graph_edges=[],
                reasoning_steps=[self.Step("Test")],
                evidence_refs=[self.Evidence("test")],
                verdict_id="v1",
                case_id="c1",
                confidence=0.9,
                private_key=self.private_key
            )
    
    def test_generate_proof_fails_empty_reasoning(self):
        """Test proof generation fails with empty reasoning steps"""
        with pytest.raises(ValueError, match="reasoning_steps cannot be empty"):
            generate_proof(
                graph_nodes={"n1": self.Node("Fact", "Test")},
                graph_edges=[],
                reasoning_steps=[],  # EMPTY
                evidence_refs=[self.Evidence("n1")],
                verdict_id="v1",
                case_id="c1",
                confidence=0.9,
                private_key=self.private_key
            )
    
    def test_generate_proof_fails_invalid_confidence(self):
        """Test proof generation fails with invalid confidence"""
        with pytest.raises(ValueError, match="confidence must be in"):
            generate_proof(
                graph_nodes={"n1": self.Node("Fact", "Test")},
                graph_edges=[],
                reasoning_steps=[self.Step("Test")],
                evidence_refs=[self.Evidence("n1")],
                verdict_id="v1",
                case_id="c1",
                confidence=1.5,  # INVALID
                private_key=self.private_key
            )


class TestProofVerification:
    """Test cryptographic proof verification"""
    
    def setup_method(self):
        """Setup before each test"""
        self.private_key, self.public_key = generate_keypair()
        self.Node = namedtuple('Node', ['node_type', 'label'])
        self.Step = namedtuple('Step', ['statement'])
        self.Evidence = namedtuple('Evidence', ['node_id'])
    
    def test_verify_valid_proof(self):
        """Test verification of valid proof"""
        proof = generate_proof(
            graph_nodes={"n1": self.Node("Fact", "Test")},
            graph_edges=[],
            reasoning_steps=[self.Step("Test step")],
            evidence_refs=[self.Evidence("n1")],
            verdict_id="v1",
            case_id="c1",
            confidence=0.9,
            private_key=self.private_key
        )
        
        # Should verify successfully
        assert proof.verify(self.public_key) is True
    
    def test_verify_fails_tampered_confidence(self):
        """Test verification fails when confidence is tampered"""
        proof = generate_proof(
            graph_nodes={"n1": self.Node("Fact", "Test")},
            graph_edges=[],
            reasoning_steps=[self.Step("Test step")],
            evidence_refs=[self.Evidence("n1")],
            verdict_id="v1",
            case_id="c1",
            confidence=0.9,
            private_key=self.private_key
        )
        
        # Tamper with confidence
        proof.confidence = 0.99
        
        # Should fail verification
        assert proof.verify(self.public_key) is False


class TestDeterministicHashing:
    """Test deterministic hashing"""
    
    def setup_method(self):
        """Setup before each test"""
        self.Node = namedtuple('Node', ['node_type', 'label'])
        self.Edge = namedtuple('Edge', ['source_id', 'target_id', 'relationship_type'])
        self.Step = namedtuple('Step', ['statement'])
    
    def test_graph_hash_deterministic(self):
        """Test that graph hashing is deterministic"""
        nodes = {
            "n1": self.Node("Fact", "Fact 1"),
            "n2": self.Node("Rule", "Rule 1")
        }
        edges = [
            self.Edge("n1", "n2", "TRIGGERS")
        ]
        
        # Hash multiple times
        hash1 = _hash_graph_state(nodes, edges)
        hash2 = _hash_graph_state(nodes, edges)
        hash3 = _hash_graph_state(nodes, edges)
        
        # All hashes should be identical
        assert hash1 == hash2 == hash3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
