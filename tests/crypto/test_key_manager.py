"""
MAHOUN KeyManager Tests - HARD MODE
=====================================

Classification: MISSION-CRITICAL / SECURITY / ARCHITECTURAL
These tests verify the KeyManager implementation with maximum rigor.

Test Coverage:
- Singleton pattern enforcement
- Thread safety
- Persistent keypair across executions
- Key version tracking
- Key rotation
- Key deletion
- Error handling
- Determinism guarantees (RULE 12)

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import os
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Optional

import pytest

from mahoun.crypto.key_manager import (
    KeyManager,
    KeyPair,
    get_key_manager,
    get_current_keypair,
    get_current_private_key,
    get_current_public_key,
    get_current_key_version,
    CURRENT_KEY_VERSION,
)
from mahoun.crypto.signatures import sign_message, verify_signature


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_key_dir():
    """Create a temporary directory for key storage."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_key_manager():
    """Reset KeyManager singleton before and after each test."""
    # Reset before test
    KeyManager._instance = None
    
    # Store original storage paths
    original_private = Path.home() / ".mahoun" / "keys" / "ed25519_private_key.pem"
    original_public = Path.home() / ".mahoun" / "keys" / "ed25519_public_key.pem"
    original_version = Path.home() / ".mahoun" / "keys" / "key_version.txt"
    
    yield
    
    # Reset after test
    KeyManager._instance = None
    
    # Clean up any test files that were created
    for f in [original_private, original_public, original_version]:
        if f.exists():
            try:
                f.unlink()
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors


# ============================================================================
# SINGLETON PATTERN TESTS
# ============================================================================

class TestSingletonPattern:
    """Test that KeyManager enforces singleton pattern."""
    
    def test_singleton_same_instance(self):
        """Verify that multiple calls return the same instance."""
        # Reset first
        KeyManager._instance = None
        
        km1 = KeyManager.get_instance()
        km2 = KeyManager.get_instance()
        
        assert km1 is km2, "KeyManager must be a singleton"
    
    def test_singleton_via_constructor(self):
        """Verify that constructor also returns singleton."""
        # Reset first
        KeyManager._instance = None
        
        km1 = KeyManager()
        km2 = KeyManager.get_instance()
        km3 = KeyManager()
        
        assert km1 is km2 is km3, "All KeyManager instances must be the same object"
    
    def test_singleton_module_level_function(self):
        """Verify that module-level get_key_manager returns singleton."""
        # Reset first
        KeyManager._instance = None
        
        km1 = get_key_manager()
        km2 = get_key_manager()
        
        assert km1 is km2, "get_key_manager must return singleton"
    
    def test_singleton_convenience_functions(self):
        """Verify that convenience functions use singleton."""
        # Reset first
        KeyManager._instance = None
        
        # Get keypair through different paths
        keypair1 = get_current_keypair()
        keypair2 = get_key_manager().get_keypair()
        
        # They should be the same keypair (same keys)
        assert keypair1.private_key_pem == keypair2.private_key_pem
        assert keypair1.public_key_pem == keypair2.public_key_pem


# ============================================================================
# KEY GENERATION AND PERSISTENCE TESTS
# ============================================================================

class TestKeyGeneration:
    """Test key generation and persistence."""
    
    def test_generates_valid_keypair(self):
        """Verify that generated keypair is cryptographically valid."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        # Verify we can sign and verify
        message = "Test message for key validation"
        signature = sign_message(message, keypair.private_key_pem)
        
        assert verify_signature(message, signature, keypair.public_key_pem), \
            "Generated keypair must produce verifiable signatures"
    
    def test_keypair_has_required_fields(self):
        """Verify that keypair has all required fields."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        assert keypair.private_key_pem, "Private key must not be empty"
        assert keypair.public_key_pem, "Public key must not be empty"
        assert keypair.version, "Key version must not be empty"
        assert len(keypair.private_key_pem) > 50, "Private key PEM must have reasonable length"
        assert len(keypair.public_key_pem) > 50, "Public key PEM must have reasonable length"
    
    def test_keypair_immutable(self):
        """Verify that KeyPair is immutable (frozen dataclass)."""
        keypair = KeyPair(
            private_key_pem="test_private",
            public_key_pem="test_public",
            version="1.0.0"
        )
        
        with pytest.raises(AttributeError):
            keypair.private_key_pem = "new_private"
        
        with pytest.raises(AttributeError):
            keypair.public_key_pem = "new_public"
    
    def test_keypair_validation(self):
        """Verify that KeyPair validates inputs."""
        with pytest.raises(ValueError, match="Private key cannot be empty"):
            KeyPair(private_key_pem="", public_key_pem="test", version="1.0.0")
        
        with pytest.raises(ValueError, match="Public key cannot be empty"):
            KeyPair(private_key_pem="test", public_key_pem="", version="1.0.0")
        
        with pytest.raises(ValueError, match="Key version cannot be empty"):
            KeyPair(private_key_pem="test", public_key_pem="test", version="")


# ============================================================================
# DETERMINISM TESTS (RULE 12)
# ============================================================================

class TestDeterminism:
    """Test that KeyManager provides deterministic keys across calls (RULE 12)."""
    
    def test_same_keypair_across_calls(self):
        """Verify that same keypair is returned across multiple calls."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        keypair1 = km.get_keypair()
        keypair2 = km.get_keypair()
        keypair3 = km.get_keypair()
        
        assert keypair1.private_key_pem == keypair2.private_key_pem
        assert keypair1.public_key_pem == keypair2.public_key_pem
        assert keypair1.version == keypair2.version
        
        assert keypair2.private_key_pem == keypair3.private_key_pem
        assert keypair2.public_key_pem == keypair3.public_key_pem
    
    def test_deterministic_signatures(self):
        """Verify that same message produces same signature (RULE 12)."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        message = "Deterministic test message"
        
        # Generate signature multiple times
        sig1 = sign_message(message, keypair.private_key_pem)
        sig2 = sign_message(message, keypair.private_key_pem)
        sig3 = sign_message(message, keypair.private_key_pem)
        
        assert sig1 == sig2 == sig3, \
            "Same message with same key must produce same signature (RULE 12)"
    
    def test_deterministic_across_convenience_functions(self):
        """Verify determinism across different access methods."""
        # Reset first
        KeyManager._instance = None
        
        message = "Test message"
        
        # Get keys through different paths
        private1 = get_current_private_key()
        private2 = get_key_manager().get_private_key()
        
        sig1 = sign_message(message, private1)
        sig2 = sign_message(message, private2)
        
        assert sig1 == sig2, "Signatures must be deterministic across access methods"


# ============================================================================
# THREAD SAFETY TESTS
# ============================================================================

class TestThreadSafety:
    """Test thread safety of KeyManager."""
    
    def test_concurrent_keypair_access(self):
        """Verify that concurrent access to keypair is thread-safe."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        results = []
        errors = []
        
        def get_keypair_worker():
            try:
                keypair = km.get_keypair()
                results.append(keypair)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=get_keypair_worker) for _ in range(10)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Concurrent access raised errors: {errors}"
        
        # Verify all got the same keypair
        assert len(results) == 10
        first_keypair = results[0]
        for keypair in results[1:]:
            assert keypair.private_key_pem == first_keypair.private_key_pem
            assert keypair.public_key_pem == first_keypair.public_key_pem
    
    def test_concurrent_signing(self):
        """Verify that concurrent signing operations work correctly."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        message = "Concurrent signing test"
        signatures = []
        errors = []
        
        def sign_worker():
            try:
                sig = sign_message(message, keypair.private_key_pem)
                signatures.append(sig)
            except Exception as e:
                errors.append(e)
        
        # Create multiple signing threads
        threads = [threading.Thread(target=sign_worker) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Concurrent signing raised errors: {errors}"
        
        # Verify all signatures are valid
        for sig in signatures:
            assert verify_signature(message, sig, keypair.public_key_pem), \
                "All concurrent signatures must be valid"


# ============================================================================
# KEY VERSION TESTS
# ============================================================================

class TestKeyVersion:
    """Test key version tracking."""
    
    def test_default_version(self):
        """Verify that default key version is CURRENT_KEY_VERSION."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        assert keypair.version == CURRENT_KEY_VERSION
    
    def test_version_from_convenience_function(self):
        """Verify that get_current_key_version returns correct version."""
        # Reset first
        KeyManager._instance = None
        
        version = get_current_key_version()
        
        assert version == CURRENT_KEY_VERSION
    
    def test_version_consistency(self):
        """Verify that version is consistent across keypair, manager, and functions."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        assert keypair.version == km.get_key_version()
        assert keypair.version == get_current_key_version()


# ============================================================================
# KEY ROTATION TESTS
# ============================================================================

class TestKeyRotation:
    """Test key rotation functionality."""
    
    def test_rotate_keys_generates_new_keypair(self):
        """Verify that rotating keys generates a new keypair."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        old_keypair = km.get_keypair()
        old_version = old_keypair.version
        
        # Rotate keys
        new_keypair = km.rotate_keys()
        
        # Verify new keypair is different
        assert new_keypair.private_key_pem != old_keypair.private_key_pem
        assert new_keypair.public_key_pem != old_keypair.public_key_pem
        
        # Verify version was incremented
        assert new_keypair.version != old_version
        
        # Verify new keypair is now the current one
        current_keypair = km.get_keypair()
        assert current_keypair.private_key_pem == new_keypair.private_key_pem
    
    def test_rotated_keys_work_cryptographically(self):
        """Verify that rotated keys still work cryptographically."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        # Rotate to new keys
        new_keypair = km.rotate_keys()
        
        # Verify new keys work
        message = "Test with rotated keys"
        signature = sign_message(message, new_keypair.private_key_pem)
        
        assert verify_signature(message, signature, new_keypair.public_key_pem), \
            "Rotated keys must produce verifiable signatures"
    
    def test_old_signatures_invalid_after_rotation(self):
        """Verify that old signatures don't verify with new keys."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        # Get old keypair
        old_keypair = km.get_keypair()
        message = "Test message"
        old_signature = sign_message(message, old_keypair.private_key_pem)
        
        # Verify old signature works with old key
        assert verify_signature(message, old_signature, old_keypair.public_key_pem)
        
        # Rotate keys
        km.rotate_keys()
        new_keypair = km.get_keypair()
        
        # Verify old signature does NOT work with new key
        assert not verify_signature(message, old_signature, new_keypair.public_key_pem), \
            "Old signatures must not verify with rotated keys"


# ============================================================================
# KEY DELETION TESTS
# ============================================================================

class TestKeyDeletion:
    """Test key deletion functionality."""
    
    def test_delete_keys_clears_memory(self):
        """Verify that delete_keys clears in-memory keypair."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        # Get a keypair
        keypair1 = km.get_keypair()
        assert keypair1 is not None
        
        # Delete keys
        km.delete_keys()
        
        # Verify new instance is created (old one still has reference)
        # We need to reset the instance to test this properly
        KeyManager._instance = None
        km2 = get_key_manager()
        
        # This should generate new keys
        keypair2 = km2.get_keypair()
        
        # New keypair should be different
        assert keypair1.private_key_pem != keypair2.private_key_pem
    
    def test_delete_keys_removes_files(self):
        """Verify that delete_keys removes key files from disk."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        # Get a keypair to ensure files exist
        keypair = km.get_keypair()
        
        # Verify files exist
        private_file = Path.home() / ".mahoun" / "keys" / "ed25519_private_key.pem"
        public_file = Path.home() / ".mahoun" / "keys" / "ed25519_public_key.pem"
        
        assert private_file.exists(), "Private key file should exist"
        assert public_file.exists(), "Public key file should exist"
        
        # Delete keys
        km.delete_keys()
        
        # Verify files are removed
        assert not private_file.exists(), "Private key file should be removed"
        assert not public_file.exists(), "Public key file should be removed"


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_get_current_private_key(self):
        """Verify get_current_private_key returns valid private key."""
        # Reset first
        KeyManager._instance = None
        
        private_key = get_current_private_key()
        
        assert private_key, "Private key must not be empty"
        assert len(private_key) > 50, "Private key must have reasonable length"
        assert "PRIVATE" in private_key or "BEGIN" in private_key, \
            "Private key should be in PEM format"
    
    def test_get_current_public_key(self):
        """Verify get_current_public_key returns valid public key."""
        # Reset first
        KeyManager._instance = None
        
        public_key = get_current_public_key()
        
        assert public_key, "Public key must not be empty"
        assert len(public_key) > 50, "Public key must have reasonable length"
        assert "PUBLIC" in public_key or "BEGIN" in public_key, \
            "Public key should be in PEM format"
    
    def test_get_current_keypair(self):
        """Verify get_current_keypair returns valid KeyPair."""
        # Reset first
        KeyManager._instance = None
        
        keypair = get_current_keypair()
        
        assert isinstance(keypair, KeyPair)
        assert keypair.private_key_pem
        assert keypair.public_key_pem
        assert keypair.version
    
    def test_convenience_functions_consistency(self):
        """Verify all convenience functions return consistent data."""
        # Reset first
        KeyManager._instance = None
        
        private_key = get_current_private_key()
        public_key = get_current_public_key()
        keypair = get_current_keypair()
        
        assert private_key == keypair.private_key_pem
        assert public_key == keypair.public_key_pem


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling in KeyManager."""
    
    def test_keypair_validation_empty_private(self):
        """Verify that empty private key raises ValueError."""
        with pytest.raises(ValueError, match="Private key cannot be empty"):
            KeyPair(private_key_pem="", public_key_pem="valid", version="1.0.0")
    
    def test_keypair_validation_empty_public(self):
        """Verify that empty public key raises ValueError."""
        with pytest.raises(ValueError, match="Public key cannot be empty"):
            KeyPair(private_key_pem="valid", public_key_pem="", version="1.0.0")
    
    def test_keypair_validation_empty_version(self):
        """Verify that empty version raises ValueError."""
        with pytest.raises(ValueError, match="Key version cannot be empty"):
            KeyPair(private_key_pem="valid", public_key_pem="valid", version="")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for KeyManager with other crypto components."""
    
    def test_integration_with_signatures(self):
        """Verify KeyManager integrates correctly with signature functions."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        message = "Integration test message"
        
        # Sign with private key from KeyManager
        signature = sign_message(message, keypair.private_key_pem)
        
        # Verify with public key from KeyManager
        assert verify_signature(message, signature, keypair.public_key_pem)
        
        # Verify with convenience function
        assert verify_signature(message, signature, get_current_public_key())
    
    def test_integration_multiple_signatures(self):
        """Verify multiple signatures with KeyManager."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        messages = [
            "First message",
            "Second message",
            "Third message",
        ]
        
        signatures = []
        for msg in messages:
            sig = sign_message(msg, keypair.private_key_pem)
            signatures.append(sig)
            # Verify immediately
            assert verify_signature(msg, sig, keypair.public_key_pem)
        
        # Verify all signatures again
        for msg, sig in zip(messages, signatures):
            assert verify_signature(msg, sig, keypair.public_key_pem)


# ============================================================================
# PRODUCTION SCENARIO TESTS
# ============================================================================

class TestProductionScenarios:
    """Test realistic production scenarios."""
    
    def test_ledger_verification_scenario(self):
        """
        Simulate a production scenario where:
        1. A verdict is signed with KeyManager keys
        2. The public key is stored in the ledger
        3. Later, someone verifies the signature using only the ledger data
        """
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        # Simulate verdict data
        verdict_data = {
            "verdict_id": "verdict_123",
            "case_id": "case_456",
            "evidence_hash": "abc123",
            "confidence": 0.95,
        }
        
        # Serialize and sign (as would happen in production)
        import json
        verdict_json = json.dumps(verdict_data, sort_keys=True)
        signature = sign_message(verdict_json, keypair.private_key_pem)
        
        # Store in "ledger" (simulated)
        ledger_entry = {
            "verdict_id": verdict_data["verdict_id"],
            "public_key": keypair.public_key_pem,
            "key_version": keypair.version,
            "signature": signature,
        }
        
        # Later: verify using only ledger data
        # This simulates independent verification without access to KeyManager
        stored_public_key = ledger_entry["public_key"]
        stored_signature = ledger_entry["signature"]
        
        is_valid = verify_signature(verdict_json, stored_signature, stored_public_key)
        
        assert is_valid, \
            "Verdict signature must verify using only ledger-stored public key"
    
    def test_key_persistence_across_restarts(self):
        """
        Test that keys persist across "restarts" (simulated by clearing singleton).
        
        This tests the scenario where:
        1. System generates keys and saves to disk
        2. System "restarts" (new process)
        3. System loads keys from disk
        """
        # Reset first
        KeyManager._instance = None
        
        # First "session"
        km1 = get_key_manager()
        keypair1 = km1.get_keypair()
        
        # Simulate restart by clearing singleton
        KeyManager._instance = None
        
        # Second "session"
        km2 = get_key_manager()
        keypair2 = km2.get_keypair()
        
        # Keys should be the same (loaded from disk)
        assert keypair1.private_key_pem == keypair2.private_key_pem
        assert keypair1.public_key_pem == keypair2.public_key_pem


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for KeyManager."""
    
    def test_keypair_access_performance(self):
        """Verify that keypair access is fast."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        
        import time
        
        # Warm up
        km.get_keypair()
        
        # Measure time for 1000 accesses
        start = time.time()
        for _ in range(1000):
            km.get_keypair()
        end = time.time()
        
        elapsed = end - start
        
        # Should be very fast (< 0.1 seconds for 1000 accesses)
        assert elapsed < 0.1, f"Keypair access too slow: {elapsed:.3f}s for 1000 accesses"
    
    def test_signing_performance(self):
        """Verify that signing with KeyManager is fast."""
        # Reset first
        KeyManager._instance = None
        
        km = get_key_manager()
        keypair = km.get_keypair()
        
        import time
        
        message = "Performance test message"
        
        # Measure time for 100 signatures
        start = time.time()
        for _ in range(100):
            sign_message(message, keypair.private_key_pem)
        end = time.time()
        
        elapsed = end - start
        
        # Should be fast (< 1 second for 100 signatures)
        assert elapsed < 1.0, f"Signing too slow: {elapsed:.3f}s for 100 signatures"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
