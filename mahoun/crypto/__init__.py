"""
Cryptographic Infrastructure for MAHOUN
========================================

Provides cryptographic primitives for:
- Digital signatures (Ed25519)
- Merkle trees for evidence verification
- Cryptographic proofs of reasoning
- Tamper-evident audit trails
"""

from typing import Optional

__version__ = "1.0.0"

# Conditional imports for graceful degradation
try:
    from .signatures import generate_keypair, sign_message, verify_signature
    from .merkle_tree import MerkleTree
    from .proof_system import CryptographicProof, generate_proof
    
    __all__ = [
        "generate_keypair",
        "sign_message",
        "verify_signature",
        "MerkleTree",
        "CryptographicProof",
        "generate_proof",
    ]
except ImportError as e:
    # Graceful degradation if cryptography not installed
    import logging
    logging.warning(f"Cryptographic features unavailable: {e}")
    __all__ = []
