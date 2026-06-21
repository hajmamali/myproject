"""
Cryptographic Proof System
===========================

Provides cryptographic proofs for:
- Graph-based reasoning verification
- Evidence integrity guarantees
- Non-repudiation of verdicts
- Tamper-evident audit trails

Architecture:
- Combines Merkle trees + digital signatures
- Binds verdict to graph state
- Enables independent verification
- Supports regulatory compliance (FDA 21 CFR Part 11)
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from mahoun.crypto.merkle_tree import MerkleTree
from mahoun.crypto.signatures import sign_message, verify_signature


class ProofSystem:
    """
    Cryptographic proof system for verdict verification
    
    Provides:
    - Proof generation
    - Signature verification
    - Merkle tree construction
    - Tamper detection
    """
    
    def __init__(self):
        """Initialize proof system"""
        pass
    
    def generate_proof(
        self,
        graph_nodes: Dict[str, Any],
        graph_edges: List[Any],
        reasoning_steps: List[Any],
        evidence_refs: List[Any],
        verdict_id: str,
        case_id: str,
        confidence: float,
        private_key: str
    ) -> 'CryptographicProof':
        """
        Generate cryptographic proof
        
        Delegates to module-level generate_proof function
        """
        return generate_proof(
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            reasoning_steps=reasoning_steps,
            evidence_refs=evidence_refs,
            verdict_id=verdict_id,
            case_id=case_id,
            confidence=confidence,
            private_key=private_key
        )


@dataclass
class CryptographicProof:
    """
    Cryptographic proof of graph-based reasoning
    
    Components:
    - graph_state_hash: Binds proof to specific graph state
    - reasoning_chain_hash: Binds proof to reasoning steps
    - evidence_merkle_root: Enables efficient evidence verification
    - timestamp: Proves when reasoning occurred
    - signature: Proves authorship and integrity
    
    Guarantees:
    - Tamper-evident: Any modification invalidates signature
    - Non-repudiable: Signature proves authorship
    - Verifiable: Anyone with public key can verify
    - Timestamped: Proves temporal ordering
    """
    
    graph_state_hash: str
    reasoning_chain_hash: str
    evidence_merkle_root: str
    timestamp: str  # ISO 8601 format
    signature: str
    
    # Metadata for verification
    verdict_id: str
    case_id: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CryptographicProof':
        """Create from dictionary"""
        return cls(**data)
    
    def verify(self, public_key: str) -> bool:
        """
        Verify proof integrity
        
        Args:
            public_key: Ed25519 public key in PEM format
        
        Returns:
            True if proof is valid, False otherwise
        
        Verification checks:
        1. Signature is valid
        2. Timestamp is reasonable (not in future)
        3. Confidence is in valid range [0, 1]
        """
        try:
            # Check confidence range
            if not (0.0 <= self.confidence <= 1.0):
                return False
            
            # Check timestamp is not in future
            proof_time = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            if proof_time > now:
                return False
            
            # Reconstruct signed message
            message = self._get_signed_message()
            
            # Verify signature
            return verify_signature(message, self.signature, public_key)
        
        except Exception:
            return False
    
    def _get_signed_message(self) -> str:
        """
        Reconstruct message that was signed
        
        Message format:
        graph_hash|reasoning_hash|merkle_root|timestamp|verdict_id|case_id|confidence
        """
        return (
            f"{self.graph_state_hash}|"
            f"{self.reasoning_chain_hash}|"
            f"{self.evidence_merkle_root}|"
            f"{self.timestamp}|"
            f"{self.verdict_id}|"
            f"{self.case_id}|"
            f"{self.confidence}"
        )
    
    def __repr__(self) -> str:
        return (
            f"CryptographicProof("
            f"verdict_id={self.verdict_id[:8]}..., "
            f"confidence={self.confidence:.2f}, "
            f"timestamp={self.timestamp})"
        )


def generate_proof(
    graph_nodes: Dict[str, Any],
    graph_edges: List[Any],
    reasoning_steps: List[Any],
    evidence_refs: List[Any],
    verdict_id: str,
    case_id: str,
    confidence: float,
    private_key: str
) -> CryptographicProof:
    """
    Generate cryptographic proof of reasoning
    
    Args:
        graph_nodes: Dictionary of graph nodes used in reasoning
        graph_edges: List of graph edges used in reasoning
        reasoning_steps: List of reasoning steps (VerdictStep objects)
        evidence_refs: List of evidence references
        verdict_id: Unique verdict identifier
        case_id: Case identifier
        confidence: Confidence score [0, 1]
        private_key: Ed25519 private key in PEM format
    
    Returns:
        CryptographicProof object
    
    Raises:
        ValueError: If inputs are invalid
        RuntimeError: If cryptography operations fail
    """
    # Validate inputs
    if not graph_nodes:
        raise ValueError("graph_nodes cannot be empty")
    if not reasoning_steps:
        raise ValueError("reasoning_steps cannot be empty")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")
    if not verdict_id or not case_id:
        raise ValueError("verdict_id and case_id must not be empty")
    
    # 1. Hash graph state (deterministic)
    graph_hash = _hash_graph_state(graph_nodes, graph_edges)
    
    # 2. Hash reasoning chain (deterministic)
    reasoning_hash = _hash_reasoning_chain(reasoning_steps)
    
    # 3. Build merkle tree of evidence
    merkle_root = _build_evidence_merkle_tree(evidence_refs)
    
    # 4. Generate timestamp
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 5. Create message to sign
    message = (
        f"{graph_hash}|"
        f"{reasoning_hash}|"
        f"{merkle_root}|"
        f"{timestamp}|"
        f"{verdict_id}|"
        f"{case_id}|"
        f"{confidence}"
    )
    
    # 6. Sign message
    signature = sign_message(message, private_key)
    
    # 7. Create proof
    return CryptographicProof(
        graph_state_hash=graph_hash,
        reasoning_chain_hash=reasoning_hash,
        evidence_merkle_root=merkle_root,
        timestamp=timestamp,
        signature=signature,
        verdict_id=verdict_id,
        case_id=case_id,
        confidence=confidence
    )


def _hash_graph_state(
    nodes: Dict[str, Any],
    edges: List[Any]
) -> str:
    """
    Hash graph state deterministically
    
    Args:
        nodes: Dictionary of graph nodes
        edges: List of graph edges
    
    Returns:
        SHA-256 hash of graph state
    
    Note:
        Uses sorted JSON to ensure determinism
    """
    # Extract node IDs and types (deterministic)
    node_data = {
        node_id: {
            "type": node.node_type if hasattr(node, 'node_type') else "unknown",
            "label": node.label if hasattr(node, 'label') else ""
        }
        for node_id, node in sorted(nodes.items())
    }
    
    # Extract edges (deterministic)
    edge_data = [
        {
            "source": edge.source_id if hasattr(edge, 'source_id') else str(edge[0]),
            "target": edge.target_id if hasattr(edge, 'target_id') else str(edge[1]),
            "type": edge.relationship_type if hasattr(edge, 'relationship_type') else "RELATED"
        }
        for edge in sorted(edges, key=lambda e: (
            e.source_id if hasattr(e, 'source_id') else str(e[0]),
            e.target_id if hasattr(e, 'target_id') else str(e[1])
        ))
    ]
    
    # Combine and hash
    graph_data = {
        "nodes": node_data,
        "edges": edge_data
    }
    
    graph_json = json.dumps(graph_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(graph_json.encode('utf-8')).hexdigest()


def _hash_reasoning_chain(steps: List[Any]) -> str:
    """
    Hash reasoning chain deterministically
    
    Args:
        steps: List of reasoning steps
    
    Returns:
        SHA-256 hash of reasoning chain
    """
    # Extract statements (deterministic)
    statements = [
        step.statement if hasattr(step, 'statement') else str(step)
        for step in steps
    ]
    
    chain_json = json.dumps(statements, ensure_ascii=False)
    return hashlib.sha256(chain_json.encode('utf-8')).hexdigest()


def _build_evidence_merkle_tree(evidence_refs: List[Any]) -> str:
    """
    Build merkle tree of evidence references
    
    Args:
        evidence_refs: List of evidence references
    
    Returns:
        Merkle root hash
    """
    if not evidence_refs:
        # Empty tree
        return hashlib.sha256(b"").hexdigest()
    
    tree = MerkleTree()
    
    for evidence in evidence_refs:
        # Extract node_id (deterministic)
        if hasattr(evidence, 'node_id'):
            node_id = evidence.node_id
        elif isinstance(evidence, dict):
            node_id = evidence.get('node_id', '')
        else:
            node_id = str(evidence)
        
        tree.add(node_id)
    
    return tree.get_root()


# Example usage
if __name__ == "__main__":
    from mahoun.crypto.signatures import generate_keypair
    
    print("🔐 Cryptographic Proof System Test")
    print("=" * 60)
    
    # Generate keypair
    private_key, public_key = generate_keypair()
    print("✓ Generated keypair")
    
    # Mock data
    from collections import namedtuple
    
    Node = namedtuple('Node', ['node_type', 'label'])
    Edge = namedtuple('Edge', ['source_id', 'target_id', 'relationship_type'])
    Step = namedtuple('Step', ['statement'])
    Evidence = namedtuple('Evidence', ['node_id'])
    
    graph_nodes = {
        "rule_219": Node("LegalRule", "Article 219"),
        "fact_0": Node("Fact", "Contract signed")
    }
    
    graph_edges = [
        Edge("fact_0", "rule_219", "TRIGGERS")
    ]
    
    reasoning_steps = [
        Step("Article 219 applies"),
        Step("Contract termination is allowed")
    ]
    
    evidence_refs = [
        Evidence("rule_219"),
        Evidence("fact_0")
    ]
    
    # Generate proof
    proof = generate_proof(
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        reasoning_steps=reasoning_steps,
        evidence_refs=evidence_refs,
        verdict_id="verdict_123",
        case_id="case_456",
        confidence=0.92,
        private_key=private_key
    )
    
    print(f"✓ Generated proof: {proof}")
    print(f"  Graph hash: {proof.graph_state_hash[:32]}...")
    print(f"  Reasoning hash: {proof.reasoning_chain_hash[:32]}...")
    print(f"  Merkle root: {proof.evidence_merkle_root[:32]}...")
    
    # Verify proof
    is_valid = proof.verify(public_key)
    print(f"✓ Proof valid: {is_valid}")
    
    # Try tampering
    proof.confidence = 0.99
    is_valid_tampered = proof.verify(public_key)
    print(f"✓ Tampered proof valid: {is_valid_tampered}")
