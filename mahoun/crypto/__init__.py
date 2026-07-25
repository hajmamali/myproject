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
    from .key_manager import (
        KeyManager,
        KeyPair,
        get_key_manager,
        get_current_keypair,
        get_current_private_key,
        get_current_public_key,
        get_current_key_version,
    )
    
    __all__ = [
        "generate_keypair",
        "sign_message",
        "verify_signature",
        "MerkleTree",
        "CryptographicProof",
        "generate_proof",
        "KeyManager",
        "KeyPair",
        "get_key_manager",
        "get_current_keypair",
        "get_current_private_key",
        "get_current_public_key",
        "get_current_key_version",
    ]
except ImportError as e:
    # Graceful degradation if cryptography not installed
    import logging
    logging.warning(f"Cryptographic features unavailable: {e}")
    __all__ = []
