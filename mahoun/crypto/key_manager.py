"""
MAHOUN Cryptographic Key Management System
===========================================

Classification: MISSION-CRITICAL / SECURITY / ARCHITECTURAL
Purpose: Centralized key management for Ed25519 keypairs ensuring:
- Single persistent keypair for the entire system (RULE 12: Determinism)
- Public key stored in ledger for future verification
- Key version tracking for rotation support
- Thread-safe access

Architectural Rules Enforced:
- RULE 12: Determinism - Same keys produce same signatures
- RULE 5: Evidence binding - Real keys for real proofs
- RULE 6: Validation result ownership - Keys enable verification

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import threading
import os
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from mahoun.crypto.signatures import generate_keypair


# ============================================================================
# KEY VERSION CONSTANTS
# ============================================================================

# Current key version - increment when rotating keys
CURRENT_KEY_VERSION = "1.0.0"

# Key storage directory
_key_dir_env = os.environ.get("MAHOUN_KEY_DIR")
KEY_STORAGE_DIR = Path(_key_dir_env) if _key_dir_env else Path.home() / ".mahoun" / "keys"
PRIVATE_KEY_FILE = KEY_STORAGE_DIR / "ed25519_private_key.pem"
PUBLIC_KEY_FILE = KEY_STORAGE_DIR / "ed25519_public_key.pem"
KEY_VERSION_FILE = KEY_STORAGE_DIR / "key_version.txt"


@dataclass(frozen=True)
class KeyPair:
    """
    Immutable container for Ed25519 keypair.
    
    Attributes:
        private_key_pem: Private key in PEM format
        public_key_pem: Public key in PEM format
        version: Key version identifier
    """
    private_key_pem: str
    public_key_pem: str
    version: str = CURRENT_KEY_VERSION
    
    def __post_init__(self):
        """Validate keypair on creation."""
        if not self.private_key_pem:
            raise ValueError("Private key cannot be empty")
        if not self.public_key_pem:
            raise ValueError("Public key cannot be empty")
        if not self.version:
            raise ValueError("Key version cannot be empty")


class KeyManager:
    """
    Thread-safe manager for Ed25519 keypairs.
    
    This manager ensures:
    1. Single persistent keypair for the entire application
    2. Keys are loaded from disk or generated once
    3. Thread-safe access to key material
    4. Key version tracking
    
    PER RULE 12: Determinism guarantee
    - The same keypair is used across all executions
    - This ensures deterministic signatures for identical inputs
    - Key regeneration only happens on explicit rotation
    
    PER RULE 5: Evidence binding
    - Real cryptographic keys are used for proof generation
    - Public key is available for verification
    
    Usage:
        # Get the global key manager
        key_manager = KeyManager.get_instance()
        
        # Get current keypair
        keypair = key_manager.get_keypair()
        
        # Sign with private key
        signature = sign_message(message, keypair.private_key_pem)
        
        # Anyone can verify with public key
        is_valid = verify_signature(message, signature, keypair.public_key_pem)
    """
    
    _instance: Optional["KeyManager"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "KeyManager":
        """Singleton pattern - only one KeyManager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize KeyManager.
        
        Creates singleton instance with lazy key loading.
        Keys are loaded on first access, not on import.
        """
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        
        self._keypair: Optional[KeyPair] = None
        self._key_lock = threading.Lock()
        self._initialized = True
        
        # Ensure storage directory exists
        self._ensure_storage_directory()
    
    @classmethod
    def get_instance(cls) -> "KeyManager":
        """
        Get the singleton KeyManager instance.
        
        Returns:
            The singleton KeyManager instance
        """
        return cls()
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (for testing only).
        
        WARNING: This should only be used in test environments.
        In production, this would break determinism guarantees.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance._keypair = None
    
    def _ensure_storage_directory(self) -> None:
        """Ensure key storage directory exists."""
        try:
            KEY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    
    def _load_keypair_from_disk(self) -> Optional[KeyPair]:
        """
        Load keypair from disk storage.
        
        Returns:
            KeyPair if both keys exist and are readable, None otherwise
        """
        if not PRIVATE_KEY_FILE.exists() or not PUBLIC_KEY_FILE.exists():
            return None
        
        try:
            with open(PRIVATE_KEY_FILE, 'r') as f:
                private_key_pem = f.read().strip()
            
            with open(PUBLIC_KEY_FILE, 'r') as f:
                public_key_pem = f.read().strip()
            
            # Load version
            version = CURRENT_KEY_VERSION
            if KEY_VERSION_FILE.exists():
                with open(KEY_VERSION_FILE, 'r') as f:
                    version = f.read().strip()
            
            return KeyPair(
                private_key_pem=private_key_pem,
                public_key_pem=public_key_pem,
                version=version
            )
        except Exception as e:
            # If loading fails, return None to trigger regeneration
            import logging
            log = logging.getLogger(__name__)
            log.error(f"Failed to load keypair from disk: {e}")
            return None
    
    def _save_keypair_to_disk(self, keypair: KeyPair) -> None:
        """
        Save keypair to disk storage.
        
        Args:
            keypair: The KeyPair to save
        """
        try:
            # Atomic write - write to temp files first, then rename
            temp_private = PRIVATE_KEY_FILE.with_suffix('.tmp')
            temp_public = PUBLIC_KEY_FILE.with_suffix('.tmp')
            temp_version = KEY_VERSION_FILE.with_suffix('.tmp')
            
            # Write files
            with open(temp_private, 'w') as f:
                f.write(keypair.private_key_pem)
            
            with open(temp_public, 'w') as f:
                f.write(keypair.public_key_pem)
            
            with open(temp_version, 'w') as f:
                f.write(keypair.version)
            
            # Atomic rename
            temp_private.rename(PRIVATE_KEY_FILE)
            temp_public.rename(PUBLIC_KEY_FILE)
            temp_version.rename(KEY_VERSION_FILE)
            
            # Set restrictive permissions (readable only by owner)
            try:
                os.chmod(PRIVATE_KEY_FILE, 0o600)
                os.chmod(PUBLIC_KEY_FILE, 0o644)
                os.chmod(KEY_VERSION_FILE, 0o644)
            except (OSError, AttributeError):
                # chmod may not be available on all platforms (Windows)
                pass
                
        except Exception as e:
            import logging
            log = logging.getLogger(__name__)
            log.error(f"Failed to save keypair to disk: {e}")
            # Clean up temp files on failure
            for temp_file in [temp_private, temp_public, temp_version]:
                if temp_file.exists():
                    temp_file.unlink()
    
    def _generate_new_keypair(self) -> KeyPair:
        """
        Generate a new Ed25519 keypair.
        
        Returns:
            New KeyPair with generated keys
        """
        private_key_pem, public_key_pem = generate_keypair()
        return KeyPair(
            private_key_pem=private_key_pem,
            public_key_pem=public_key_pem,
            version=CURRENT_KEY_VERSION
        )
    
    def get_keypair(self) -> KeyPair:
        """
        Get the current Ed25519 keypair.
        
        This method is thread-safe and guarantees:
        - Same keypair is returned for all calls within same process
        - Keys are loaded from disk if available
        - Keys are generated and persisted if not available
        
        PER RULE 12: Determinism
        The same keypair is always returned, ensuring deterministic
        signature generation for identical inputs.
        
        Returns:
            KeyPair containing private and public keys
        """
        if self._keypair is not None:
            return self._keypair
        
        with self._key_lock:
            # Double-check after acquiring lock
            if self._keypair is not None:
                return self._keypair
            
            # Try to load from disk
            keypair = self._load_keypair_from_disk()
            
            if keypair is None:
                # Generate new keypair
                keypair = self._generate_new_keypair()
                # Save to disk for persistence
                self._save_keypair_to_disk(keypair)
                
                import logging
                log = logging.getLogger(__name__)
                log.info(f"Generated new Ed25519 keypair (version {keypair.version})")
            else:
                import logging
                log = logging.getLogger(__name__)
                log.info(f"Loaded Ed25519 keypair from disk (version {keypair.version})")
            
            self._keypair = keypair
            return self._keypair
    
    def get_public_key(self) -> str:
        """
        Get the current public key (PEM format).
        
        This can be freely distributed for signature verification.
        
        Returns:
            Public key in PEM format
        """
        return self.get_keypair().public_key_pem
    
    def get_private_key(self) -> str:
        """
        Get the current private key (PEM format).
        
        WARNING: Private key must be kept secure.
        Access should be restricted to signing operations only.
        
        Returns:
            Private key in PEM format
        """
        return self.get_keypair().private_key_pem
    
    def get_key_version(self) -> str:
        """
        Get the current key version.
        
        Returns:
            Key version identifier
        """
        return self.get_keypair().version
    
    def rotate_keys(self) -> KeyPair:
        """
        Rotate to a new keypair.
        
        This method:
        1. Generates a new keypair
        2. Saves it to disk
        3. Updates the in-memory keypair
        
        WARNING: Key rotation breaks determinism for existing signatures.
        This should only be done for security reasons (key compromise).
        
        Returns:
            The new KeyPair
        """
        import logging
        log = logging.getLogger(__name__)
        
        with self._key_lock:
            # Increment version
            old_keypair = self._keypair
            old_version = old_keypair.version if old_keypair else "0.0.0"
            
            # Parse version and increment
            try:
                parts = old_version.split('.')
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                new_version = f"{major}.{minor}.{patch + 1}"
            except (ValueError, IndexError):
                new_version = "1.0.0"
            
            # Generate new keypair
            new_keypair = self._generate_new_keypair()
            new_keypair = KeyPair(
                private_key_pem=new_keypair.private_key_pem,
                public_key_pem=new_keypair.public_key_pem,
                version=new_version
            )
            
            # Save to disk
            self._save_keypair_to_disk(new_keypair)
            
            # Update in-memory
            self._keypair = new_keypair
            
            log.warning(
                f"KEY ROTATION: Old version {old_version} replaced with {new_version}. "
                f"Existing signatures will no longer verify!"
            )
            
            return new_keypair
    
    def delete_keys(self) -> None:
        """
        Delete stored keys from disk.
        
        WARNING: This will cause new keys to be generated on next access.
        Existing signatures will no longer verify.
        
        This should only be used for testing or system cleanup.
        """
        import logging
        log = logging.getLogger(__name__)
        
        with self._key_lock:
            # Delete files
            for key_file in [PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, KEY_VERSION_FILE]:
                if key_file.exists():
                    key_file.unlink()
            
            # Clear in-memory
            self._keypair = None
            
            log.warning("All cryptographic keys have been deleted from disk and memory")


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

def get_key_manager() -> KeyManager:
    """
    Get the global KeyManager instance.
    
    This is the recommended way to access key management functionality.
    
    Returns:
        The singleton KeyManager instance
    
    Usage:
        from mahoun.crypto.key_manager import get_key_manager
        
        key_manager = get_key_manager()
        keypair = key_manager.get_keypair()
    """
    return KeyManager.get_instance()


def get_current_keypair() -> KeyPair:
    """
    Get the current Ed25519 keypair (convenience function).
    
    Returns:
        Current KeyPair
    """
    return get_key_manager().get_keypair()


def get_current_private_key() -> str:
    """
    Get the current private key (convenience function).
    
    WARNING: Private key must be kept secure.
    
    Returns:
        Private key in PEM format
    """
    return get_key_manager().get_private_key()


def get_current_public_key() -> str:
    """
    Get the current public key (convenience function).
    
    Returns:
        Public key in PEM format
    """
    return get_key_manager().get_public_key()


def get_current_key_version() -> str:
    """
    Get the current key version (convenience function).
    
    Returns:
        Key version identifier
    """
    return get_key_manager().get_key_version()


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Initialize KeyManager (lazy - actual key loading happens on first access)
_key_manager = KeyManager.get_instance()

# Export public API
__all__ = [
    "KeyManager",
    "KeyPair",
    "CURRENT_KEY_VERSION",
    "get_key_manager",
    "get_current_keypair",
    "get_current_private_key",
    "get_current_public_key",
    "get_current_key_version",
]
