"""
API Key Collision Prevention Tests - Wave 1, Week 1

Coverage Target:
- api_keys.py _hash_key() method (line 89)
- Key generation uniqueness guarantees

Critical Paths:
- Hash collision detection
- Key uniqueness across large scale
- Birthday paradox resistance

Risk Mitigation:
- P0 Security: Key collision → unauthorized access via predictable keys
- P0 Security: Hash weakness → key guessing attacks
"""

import pytest
from mahoun.security.api_keys import APIKeyManager, KeyStatus


@pytest.fixture
def api_key_manager():
    """Fresh APIKeyManager for each test."""
    return APIKeyManager()


class TestKeyCollisionPrevention:
    """Test cryptographic uniqueness and collision resistance."""
    
    def test_no_collisions_in_10000_keys(self, api_key_manager):
        """CRITICAL: Verify no collisions in 10,000 generated keys."""
        keys = []
        key_hashes = []
        key_ids = []
        
        for i in range(10000):
            key, meta = api_key_manager.generate_key(f"test_{i}")
            keys.append(key)
            key_hashes.append(meta.key_hash)
            key_ids.append(meta.key_id)
        
        # All keys unique
        assert len(keys) == len(set(keys)), "Keys must all be unique"
        
        # All hashes unique
        assert len(key_hashes) == len(set(key_hashes)), "Key hashes must all be unique"
        
        # All IDs unique
        assert len(key_ids) == len(set(key_ids)), "Key IDs must all be unique"
    
    def test_hash_function_deterministic(self, api_key_manager):
        """Verify hash function is deterministic."""
        test_key = "mhn_test_key_12345"
        
        hash1 = api_key_manager._hash_key(test_key)
        hash2 = api_key_manager._hash_key(test_key)
        
        assert hash1 == hash2, "Same key must produce same hash"
    
    def test_hash_function_avalanche_effect(self, api_key_manager):
        """Verify small changes produce completely different hashes."""
        key1 = "mhn_test_key_12345"
        key2 = "mhn_test_key_12346"  # Single character different
        
        hash1 = api_key_manager._hash_key(key1)
        hash2 = api_key_manager._hash_key(key2)
        
        assert hash1 != hash2, "Different keys must produce different hashes"
        
        # Count different bits (avalanche effect)
        diff_bits = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        # SHA256 should have ~50% bits different
        assert diff_bits > 20, f"Only {diff_bits}/64 hex digits different - poor avalanche"
    
    def test_hash_output_length(self, api_key_manager):
        """Verify SHA256 hash is correct length."""
        key = "mhn_test_key"
        hash_output = api_key_manager._hash_key(key)
        
        # SHA256 produces 64 hex characters
        assert len(hash_output) == 64, f"Hash length {len(hash_output)} != 64"
        
        # All characters should be valid hex
        assert all(c in "0123456789abcdef" for c in hash_output), "Non-hex characters in hash"
    
    def test_key_prefix_enforced(self, api_key_manager):
        """Verify all keys have correct prefix."""
        keys = [api_key_manager.generate_key(f"test{i}")[0] for i in range(100)]
        
        for key in keys:
            assert key.startswith("mhn_"), f"Key {key} missing prefix"
    
    def test_concurrent_key_generation_no_collision(self, api_key_manager):
        """Verify concurrent-like generation produces unique keys."""
        # Simulate rapid generation (no actual threading to keep tests simple)
        keys = [api_key_manager.generate_key("test")[0] for _ in range(1000)]
        
        assert len(keys) == len(set(keys)), "Rapid generation must not produce collisions"
    
    def test_key_id_uniqueness(self, api_key_manager):
        """Verify key IDs are globally unique."""
        key_ids = set()
        
        for i in range(5000):
            _, meta = api_key_manager.generate_key(f"test_{i}")
            assert meta.key_id not in key_ids, f"Key ID collision at iteration {i}"
            key_ids.add(meta.key_id)
    
    def test_hash_collision_different_keys_same_name(self, api_key_manager):
        """Verify different keys with same name don't collide."""
        key1, meta1 = api_key_manager.generate_key("duplicate_name")
        key2, meta2 = api_key_manager.generate_key("duplicate_name")
        
        # Keys should be different even with same name
        assert key1 != key2
        assert meta1.key_hash != meta2.key_hash
        assert meta1.key_id != meta2.key_id


class TestKeyEntropyValidation:
    """Test cryptographic entropy of generated keys."""
    
    def test_key_entropy_sufficient(self, api_key_manager):
        """Verify keys have sufficient entropy."""
        keys = [api_key_manager.generate_key(f"test{i}")[0] for i in range(100)]
        
        for key in keys:
            # Remove prefix
            key_body = key[4:]  # Skip "mhn_"
            
            # Check length (32 bytes base64 = 43+ chars)
            assert len(key_body) >= 40, f"Key body {len(key_body)} too short"
            
            # Check character diversity (should use full base64 alphabet)
            unique_chars = len(set(key_body))
            assert unique_chars > 20, f"Only {unique_chars} unique characters - low entropy"
    
    def test_key_randomness_distribution(self, api_key_manager):
        """Verify key bytes have uniform distribution."""
        keys = [api_key_manager.generate_key(f"test{i}")[0] for i in range(100)]
        
        # Collect all characters
        all_chars = ''.join(k[4:] for k in keys)  # Skip prefixes
        
        # Count frequency
        from collections import Counter
        freq = Counter(all_chars)
        
        # Each character should appear roughly equally
        # (This is a weak test, but catches obvious bias)
        most_common = freq.most_common(1)[0][1]
        least_common = freq.most_common()[-1][1]
        
        # Ratio shouldn't be extreme
        ratio = most_common / least_common if least_common > 0 else float('inf')
        assert ratio < 5, f"Character distribution ratio {ratio} too skewed"


class TestKeyValidationUniqueness:
    """Test key validation uniqueness guarantees."""
    
    def test_validate_only_correct_key(self, api_key_manager):
        """Verify only the exact key validates."""
        key1, meta1 = api_key_manager.generate_key("test1")
        key2, meta2 = api_key_manager.generate_key("test2")
        
        # key1 should validate to meta1
        validated1 = api_key_manager.validate_key(key1)
        assert validated1.key_id == meta1.key_id
        
        # key2 should validate to meta2
        validated2 = api_key_manager.validate_key(key2)
        assert validated2.key_id == meta2.key_id
        
        # No cross-validation
        assert validated1.key_id != meta2.key_id
        assert validated2.key_id != meta1.key_id
    
    def test_modified_key_fails_validation(self, api_key_manager):
        """CRITICAL: Modified key must not validate."""
        key, meta = api_key_manager.generate_key("test")
        
        # Modify key slightly
        modified_key = key[:-1] + ("a" if key[-1] != "a" else "b")
        
        validated = api_key_manager.validate_key(modified_key)
        assert validated is None, "Modified key must not validate"
