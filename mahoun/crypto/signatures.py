"""
Ed25519 Digital Signatures
===========================

Provides cryptographic signatures for:
- Verdict authentication
- Ledger entry signing
- Proof of authorship
- Non-repudiation

Uses Ed25519 (RFC 8032) for:
- Fast signing/verification
- Small signature size (64 bytes)
- Strong security (128-bit)
"""

import base64
from typing import Tuple

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def generate_keypair() -> Tuple[str, str]:
    """
    Generate Ed25519 keypair
    
    Returns:
        Tuple of (private_key_pem, public_key_pem)
    
    Raises:
        RuntimeError: If cryptography library not available
    """
    if not HAS_CRYPTO:
        raise RuntimeError(
            "Cryptography library not installed. "
            "Install with: pip install cryptography>=41.0.0"
        )
    
    # Generate private key
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Serialize to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode('utf-8'), public_pem.decode('utf-8')


def sign_message(message: str, private_key_pem: str) -> str:
    """
    Sign message with Ed25519 private key
    
    Args:
        message: Message to sign
        private_key_pem: Private key in PEM format
    
    Returns:
        Base64-encoded signature
    
    Raises:
        RuntimeError: If cryptography library not available
        ValueError: If private key is invalid
    """
    if not HAS_CRYPTO:
        raise RuntimeError(
            "Cryptography library not installed. "
            "Install with: pip install cryptography>=41.0.0"
        )
    
    try:
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None
        )
        
        # Sign message
        signature = private_key.sign(message.encode('utf-8'))
        
        # Return base64-encoded signature
        return base64.b64encode(signature).decode('utf-8')
    
    except Exception as e:
        raise ValueError(f"Failed to sign message: {e}") from e


def verify_signature(message: str, signature: str, public_key_pem: str) -> bool:
    """
    Verify Ed25519 signature
    
    Args:
        message: Original message
        signature: Base64-encoded signature
        public_key_pem: Public key in PEM format
    
    Returns:
        True if signature is valid, False otherwise
    
    Raises:
        RuntimeError: If cryptography library not available
    """
    if not HAS_CRYPTO:
        raise RuntimeError(
            "Cryptography library not installed. "
            "Install with: pip install cryptography>=41.0.0"
        )
    
    try:
        # Load public key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8')
        )
        
        # Decode signature
        sig_bytes = base64.b64decode(signature)
        
        # Verify signature
        public_key.verify(sig_bytes, message.encode('utf-8'))
        
        return True
    
    except InvalidSignature:
        return False
    except Exception:
        return False


# Example usage
if __name__ == "__main__":
    # Generate keypair
    private_key, public_key = generate_keypair()
    print(f"Private key: {private_key[:50]}...")
    print(f"Public key: {public_key[:50]}...")
    
    # Sign message
    message = "This is a test verdict"
    signature = sign_message(message, private_key)
    print(f"Signature: {signature[:50]}...")
    
    # Verify signature
    is_valid = verify_signature(message, signature, public_key)
    print(f"Signature valid: {is_valid}")
    
    # Try tampering
    tampered_message = "This is a tampered verdict"
    is_valid_tampered = verify_signature(tampered_message, signature, public_key)
    print(f"Tampered signature valid: {is_valid_tampered}")
