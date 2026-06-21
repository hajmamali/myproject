"""
Merkle Tree for Evidence Verification
======================================

Provides tamper-evident data structures for:
- Evidence integrity verification
- Efficient proof of inclusion
- Compact cryptographic commitments
- Audit trail verification

Properties:
- O(log n) proof size
- O(n) construction time
- Tamper-evident (any change invalidates root)
- Deterministic (same input = same root)
"""

import hashlib
from typing import List, Optional, Tuple


class MerkleTree:
    """
    Merkle tree implementation for evidence verification
    
    Guarantees:
    - Deterministic root computation
    - Tamper detection
    - Efficient proof generation
    - Cryptographic binding to evidence
    """
    
    def __init__(self):
        self.leaves: List[str] = []
        self._root: Optional[str] = None
        self._tree_levels: List[List[str]] = []
    
    def add(self, data: str) -> None:
        """
        Add leaf to merkle tree
        
        Args:
            data: Data to add (will be hashed)
        
        Note:
            Invalidates cached root. Call get_root() to recompute.
        """
        if not data:
            raise ValueError("Cannot add empty data to merkle tree")
        
        # Hash the data to create leaf
        leaf_hash = hashlib.sha256(data.encode('utf-8')).hexdigest()
        self.leaves.append(leaf_hash)
        
        # Invalidate cached root
        self._root = None
        self._tree_levels = []
    
    def get_root(self) -> str:
        """
        Compute merkle root
        
        Returns:
            SHA-256 hash of merkle root
        
        Note:
            Returns hash of empty string if tree is empty.
            Result is cached until tree is modified.
            Root is deterministic regardless of insertion order.
        """
        # Return cached root if available
        if self._root is not None:
            return self._root
        
        # Handle empty tree
        if not self.leaves:
            self._root = hashlib.sha256(b"").hexdigest()
            return self._root
        
        # Build tree bottom-up with sorted leaves for determinism
        current_level = sorted(self.leaves)
        self._tree_levels = [current_level[:]]
        
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                
                # If odd number of nodes, duplicate last one
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Combine and hash
                combined = f"{left}{right}"
                parent_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
                next_level.append(parent_hash)
            
            self._tree_levels.append(next_level[:])
            current_level = next_level
        
        # Root is the single remaining hash
        self._root = current_level[0]
        return self._root
    
    def get_proof(self, leaf_index: int) -> List[Tuple[str, str]]:
        """
        Generate merkle proof for leaf at index
        
        Args:
            leaf_index: Index of leaf to prove
        
        Returns:
            List of (hash, position) tuples for proof path
            Position is 'left' or 'right'
        
        Raises:
            ValueError: If index is out of bounds
            RuntimeError: If tree hasn't been built yet
        """
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise ValueError(f"Leaf index {leaf_index} out of bounds [0, {len(self.leaves)})")
        
        # Ensure tree is built
        if not self._tree_levels:
            self.get_root()
        
        proof: List[Tuple[str, str]] = []
        current_index = leaf_index
        
        # Traverse from leaf to root
        for level in self._tree_levels[:-1]:  # Exclude root level
            # Determine sibling index
            if current_index % 2 == 0:
                # Current is left child, sibling is right
                sibling_index = current_index + 1
                position = 'right'
            else:
                # Current is right child, sibling is left
                sibling_index = current_index - 1
                position = 'left'
            
            # Add sibling to proof (if exists)
            if sibling_index < len(level):
                proof.append((level[sibling_index], position))
            else:
                # Odd number of nodes, sibling is duplicate of current
                proof.append((level[current_index], position))
            
            # Move to parent level
            current_index = current_index // 2
        
        return proof
    
    def verify_proof(
        self,
        leaf_data: str,
        proof: List[Tuple[str, str]],
        root: str
    ) -> bool:
        """
        Verify merkle proof
        
        Args:
            leaf_data: Original leaf data
            proof: Merkle proof from get_proof()
            root: Expected merkle root
        
        Returns:
            True if proof is valid, False otherwise
        """
        # Hash leaf data
        current_hash = hashlib.sha256(leaf_data.encode('utf-8')).hexdigest()
        
        # Apply proof path
        for sibling_hash, position in proof:
            if position == 'left':
                combined = f"{sibling_hash}{current_hash}"
            else:
                combined = f"{current_hash}{sibling_hash}"
            
            current_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        # Check if we arrived at expected root
        return current_hash == root
    
    def __len__(self) -> int:
        """Return number of leaves in tree"""
        return len(self.leaves)
    
    def __repr__(self) -> str:
        """String representation"""
        root = self.get_root()
        return f"MerkleTree(leaves={len(self.leaves)}, root={root[:16]}...)"


# Example usage and testing
if __name__ == "__main__":
    print("🌳 Merkle Tree Test")
    print("=" * 60)
    
    # Create tree
    tree = MerkleTree()
    
    # Add evidence
    evidence = [
        "rule_219: Article 219 of Civil Code",
        "precedent_1234: Supreme Court Case 1234",
        "fact_0: Contract was signed on 2024-01-15",
        "fact_1: Party A violated clause 3.2"
    ]
    
    for item in evidence:
        tree.add(item)
    
    # Get root
    root = tree.get_root()
    print(f"✓ Merkle root: {root[:32]}...")
    print(f"✓ Tree size: {len(tree)} leaves")
    
    # Generate proof for first item
    proof = tree.get_proof(0)
    print(f"✓ Proof size: {len(proof)} hashes")
    
    # Verify proof
    is_valid = tree.verify_proof(evidence[0], proof, root)
    print(f"✓ Proof valid: {is_valid}")
    
    # Try tampering
    tampered_evidence = "rule_219: FAKE ARTICLE"
    is_valid_tampered = tree.verify_proof(tampered_evidence, proof, root)
    print(f"✓ Tampered proof valid: {is_valid_tampered}")
    
    # Demonstrate tamper detection
    print("\n🔒 Tamper Detection Test")
    tree2 = MerkleTree()
    for item in evidence:
        tree2.add(item)
    
    root2 = tree2.get_root()
    print(f"✓ Original root: {root[:32]}...")
    
    # Modify one item
    tree2.leaves[0] = hashlib.sha256(b"TAMPERED").hexdigest()
    tree2._root = None  # Invalidate cache
    root2_tampered = tree2.get_root()
    print(f"✓ Tampered root: {root2_tampered[:32]}...")
    print(f"✓ Roots match: {root == root2_tampered}")
