"""
API Key Lifecycle Tests - Wave 1, Week 1

Coverage Target:
- api_keys.py lines 89-234 (generation, rotation, revocation, expiry)

Critical Paths:
- Key generation uniqueness
- Key rotation security
- Revocation enforcement
- Expiry validation
- Status transitions

Risk Mitigation:
- P0 Security: Key reuse after revocation (bypass attempt)
- P0 Security: Expired key acceptance (time-based bypass)
- P0 Security: Key collision (hash weakness)
"""

import pytest
from datetime import datetime, timedelta, timezone
from mahoun.security.api_keys import APIKeyManager, APIKey, KeyStatus


@pytest.fixture
def api_key_manager():
    """Fresh APIKeyManager for each test."""
    return APIKeyManager()


@pytest.fixture
def sample_key(api_key_manager):
    """Generate a sample key for testing."""
    key, meta = api_key_manager.generate_key(
        name="test_key",
        permissions=["read", "write"],
        rate_limit=100
    )
    return key, meta


class TestAPIKeyGeneration:
    """Test key generation security and uniqueness."""
    
    @pytest.mark.p1
    def test_key_generation_creates_unique_keys(self, api_key_manager):
        """Verify generated keys are cryptographically unique."""
        key1, meta1 = api_key_manager.generate_key("test1")
        key2, meta2 = api_key_manager.generate_key("test2")
        
        assert key1 != key2, "Keys must be unique"
        assert meta1.key_id != meta2.key_id, "Key IDs must be unique"
        assert meta1.key_hash != meta2.key_hash, "Key hashes must be unique"
    
    @pytest.mark.p1
    def test_key_generation_uses_secure_random(self, api_key_manager):
        """Verify keys use cryptographically secure randomness."""
        keys = [api_key_manager.generate_key(f"test{i}")[0] for i in range(100)]
        
        # Check no duplicates in 100 keys
        assert len(keys) == len(set(keys)), "100 keys must all be unique"
        
        # Check sufficient entropy (key length)
        for key in keys:
            assert len(key) >= 40, f"Key length {len(key)} insufficient"
            assert key.startswith("mhn_"), "Key must have correct prefix"
    
    @pytest.mark.p1
    def test_key_generation_with_permissions(self, api_key_manager):
        """Verify permissions are correctly assigned."""
        key, meta = api_key_manager.generate_key(
            "test",
            permissions=["read", "write", "delete"]
        )
        
        assert meta.permissions == ["read", "write", "delete"]
        assert meta.status == KeyStatus.ACTIVE
    
    @pytest.mark.p1
    def test_key_generation_with_expiry(self, api_key_manager):
        """Verify expiry is correctly set."""
        key, meta = api_key_manager.generate_key(
            "test",
            expires_in_days=7
        )
        
        assert meta.expires_at is not None
        expected_expiry = datetime.now(timezone.utc) + timedelta(days=7)
        # Allow 1 second tolerance
        assert abs((meta.expires_at - expected_expiry).total_seconds()) < 1
    
    @pytest.mark.p1
    def test_key_generation_without_expiry(self, api_key_manager):
        """Verify keys can be created without expiry."""
        key, meta = api_key_manager.generate_key("test")
        
        assert meta.expires_at is None, "Key should not expire"
    
    @pytest.mark.p1
    def test_key_generation_with_rate_limit(self, api_key_manager):
        """Verify rate limit is correctly assigned."""
        key, meta = api_key_manager.generate_key(
            "test",
            rate_limit=50
        )
        
        assert meta.rate_limit == 50
    
    @pytest.mark.p1
    def test_key_generation_with_metadata(self, api_key_manager):
        """Verify custom metadata is stored."""
        custom_meta = {"user_id": "123", "team": "engineering"}
        key, meta = api_key_manager.generate_key(
            "test",
            metadata=custom_meta
        )
        
        assert meta.metadata == custom_meta
    
    @pytest.mark.p1
    def test_key_hash_storage(self, api_key_manager):
        """Verify raw key is never stored, only hash."""
        key, meta = api_key_manager.generate_key("test")
        
        # Hash should be stored
        assert meta.key_hash is not None
        assert len(meta.key_hash) == 64  # SHA256 hex digest
        
        # Raw key should not be in stored metadata
        assert key not in str(meta.to_dict())


class TestAPIKeyRotation:
    """Test key rotation security - CRITICAL P0."""
    
    @pytest.mark.p1
    def test_key_rotation_generates_new_key(self, api_key_manager, sample_key):
        """Verify rotation generates a completely new key."""
        old_key, old_meta = sample_key
        
        new_key, new_meta = api_key_manager.rotate_key(old_meta.key_id)
        
        assert new_key != old_key, "New key must be different"
        assert new_meta.key_id != old_meta.key_id, "New key ID must be different"
        assert new_meta.key_hash != old_meta.key_hash, "New key hash must be different"
    
    @pytest.mark.p1
    def test_key_rotation_revokes_old_key(self, api_key_manager, sample_key):
        """CRITICAL: Verify old key is immediately revoked after rotation."""
        old_key, old_meta = sample_key
        
        # Rotate
        new_key, new_meta = api_key_manager.rotate_key(old_meta.key_id)
        
        # Old key should be revoked
        validated = api_key_manager.validate_key(old_key)
        assert validated is None, "Old key must be invalid after rotation"
        assert old_meta.status == KeyStatus.REVOKED, "Old key status must be REVOKED"
    
    @pytest.mark.p1
    def test_key_rotation_preserves_permissions(self, api_key_manager):
        """Verify permissions are carried over to new key."""
        key, meta = api_key_manager.generate_key(
            "test",
            permissions=["read", "admin"]
        )
        
        new_key, new_meta = api_key_manager.rotate_key(meta.key_id)
        
        assert new_meta.permissions == meta.permissions
    
    @pytest.mark.p1
    def test_key_rotation_preserves_rate_limit(self, api_key_manager):
        """Verify rate limit is carried over to new key."""
        key, meta = api_key_manager.generate_key("test", rate_limit=75)
        
        new_key, new_meta = api_key_manager.rotate_key(meta.key_id)
        
        assert new_meta.rate_limit == 75
    
    @pytest.mark.p1
    def test_key_rotation_resets_expiry(self, api_key_manager):
        """Verify expiry is reset (not carried over)."""
        key, meta = api_key_manager.generate_key("test", expires_in_days=1)
        
        new_key, new_meta = api_key_manager.rotate_key(meta.key_id)
        
        # New key should have no expiry
        assert new_meta.expires_at is None
    
    @pytest.mark.p1
    def test_key_rotation_adds_metadata(self, api_key_manager, sample_key):
        """Verify rotation is tracked in metadata."""
        old_key, old_meta = sample_key
        
        new_key, new_meta = api_key_manager.rotate_key(old_meta.key_id)
        
        assert "rotated_from" in new_meta.metadata
        assert new_meta.metadata["rotated_from"] == old_meta.key_id
    
    @pytest.mark.p1
    def test_key_rotation_nonexistent_key(self, api_key_manager):
        """Verify rotation fails gracefully for nonexistent key."""
        result = api_key_manager.rotate_key("nonexistent_key_id")
        
        assert result is None, "Should return None for nonexistent key"
    
    @pytest.mark.p1
    def test_key_rotation_new_key_works(self, api_key_manager, sample_key):
        """Verify new key is immediately usable."""
        old_key, old_meta = sample_key
        
        new_key, new_meta = api_key_manager.rotate_key(old_meta.key_id)
        
        # New key should validate
        validated = api_key_manager.validate_key(new_key)
        assert validated is not None
        assert validated.key_id == new_meta.key_id


class TestAPIKeyRevocation:
    """Test key revocation enforcement - CRITICAL P0."""
    
    @pytest.mark.p1
    def test_key_revocation_changes_status(self, api_key_manager, sample_key):
        """Verify revocation changes key status."""
        key, meta = sample_key
        
        success = api_key_manager.revoke_key(meta.key_id)
        
        assert success is True
        assert meta.status == KeyStatus.REVOKED
    
    @pytest.mark.p1
    def test_revoked_key_cannot_validate(self, api_key_manager, sample_key):
        """CRITICAL: Revoked keys must not validate."""
        key, meta = sample_key
        
        # Revoke the key
        api_key_manager.revoke_key(meta.key_id)
        
        # Attempt to validate
        validated = api_key_manager.validate_key(key)
        assert validated is None, "Revoked key must not validate"
    
    @pytest.mark.p1
    def test_revoke_nonexistent_key(self, api_key_manager):
        """Verify revocation fails gracefully for nonexistent key."""
        success = api_key_manager.revoke_key("nonexistent")
        
        assert success is False
    
    @pytest.mark.p1
    def test_revoke_already_revoked_key(self, api_key_manager, sample_key):
        """Verify double revocation is idempotent."""
        key, meta = sample_key
        
        api_key_manager.revoke_key(meta.key_id)
        success = api_key_manager.revoke_key(meta.key_id)
        
        assert success is True
        assert meta.status == KeyStatus.REVOKED



class TestAPIKeyExpiry:
    """Test key expiry enforcement - CRITICAL P0."""
    
    @pytest.mark.p1
    def test_expired_key_status_update(self, api_key_manager):
        """Verify expired key status is updated on validation."""
        # Create key that expires in 1 microsecond
        key, meta = api_key_manager.generate_key(
            "test",
            expires_in_days=0  # Will be in past after processing
        )
        
        # Manually set expiry to past
        meta.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        # Validate should fail and update status
        validated = api_key_manager.validate_key(key)
        assert validated is None
        assert meta.status == KeyStatus.EXPIRED
    
    @pytest.mark.p1
    def test_key_expiry_boundary(self, api_key_manager):
        """Test expiry boundary condition."""
        key, meta = api_key_manager.generate_key("test", expires_in_days=1)
        
        # Key should be valid now
        validated = api_key_manager.validate_key(key)
        assert validated is not None
        
        # Manually expire it
        meta.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        # Should now be invalid
        validated = api_key_manager.validate_key(key)
        assert validated is None
    
    @pytest.mark.p1
    def test_non_expiring_key_remains_valid(self, api_key_manager):
        """Verify keys without expiry remain valid indefinitely."""
        key, meta = api_key_manager.generate_key("test")  # No expiry
        
        # Should validate
        validated = api_key_manager.validate_key(key)
        assert validated is not None
        
        # Should still validate after "long time"
        # (We can't actually wait, so this tests the logic)
        assert meta.expires_at is None


class TestAPIKeySuspension:
    """Test key suspension and reactivation."""
    
    @pytest.mark.p1
    def test_key_suspension_changes_status(self, api_key_manager, sample_key):
        """Verify suspension changes key status."""
        key, meta = sample_key
        
        success = api_key_manager.suspend_key(meta.key_id)
        
        assert success is True
        assert meta.status == KeyStatus.SUSPENDED
    
    @pytest.mark.p1
    def test_suspended_key_cannot_validate(self, api_key_manager, sample_key):
        """Suspended keys must not validate."""
        key, meta = sample_key
        
        api_key_manager.suspend_key(meta.key_id)
        
        validated = api_key_manager.validate_key(key)
        assert validated is None
    
    @pytest.mark.p1
    def test_key_reactivation_from_suspended(self, api_key_manager, sample_key):
        """Verify suspended keys can be reactivated."""
        key, meta = sample_key
        
        api_key_manager.suspend_key(meta.key_id)
        success = api_key_manager.reactivate_key(meta.key_id)
        
        assert success is True
        assert meta.status == KeyStatus.ACTIVE
        
        # Should now validate
        validated = api_key_manager.validate_key(key)
        assert validated is not None
    
    @pytest.mark.p1
    def test_key_reactivation_from_revoked_fails(self, api_key_manager, sample_key):
        """Verify revoked keys cannot be reactivated (security)."""
        key, meta = sample_key
        
        api_key_manager.revoke_key(meta.key_id)
        success = api_key_manager.reactivate_key(meta.key_id)
        
        assert success is False, "Revoked keys must not be reactivatable"
        assert meta.status == KeyStatus.REVOKED


class TestAPIKeyValidation:
    """Test key validation logic."""
    
    @pytest.mark.p1
    def test_valid_key_updates_usage_count(self, api_key_manager, sample_key):
        """Verify validation increments usage count."""
        key, meta = sample_key
        
        initial_count = meta.usage_count
        api_key_manager.validate_key(key)
        
        assert meta.usage_count == initial_count + 1
    
    @pytest.mark.p1
    def test_valid_key_updates_last_used(self, api_key_manager, sample_key):
        """Verify validation updates last_used timestamp."""
        key, meta = sample_key
        
        assert meta.last_used is None
        
        api_key_manager.validate_key(key)
        
        assert meta.last_used is not None
        # Should be very recent
        assert (datetime.now(timezone.utc) - meta.last_used).total_seconds() < 1
    
    @pytest.mark.p1
    def test_invalid_key_returns_none(self, api_key_manager):
        """Verify invalid keys return None."""
        validated = api_key_manager.validate_key("invalid_key")
        assert validated is None
    
    @pytest.mark.p1
    def test_malformed_key_returns_none(self, api_key_manager):
        """Verify malformed keys return None."""
        validated = api_key_manager.validate_key("")
        assert validated is None
        
        validated = api_key_manager.validate_key("no_prefix_key")
        assert validated is None


class TestAPIKeyPermissions:
    """Test permission checking logic."""
    
    @pytest.mark.p1
    def test_check_permission_with_permission(self, api_key_manager):
        """Verify permission check succeeds with correct permission."""
        key, meta = api_key_manager.generate_key(
            "test",
            permissions=["read", "write"]
        )
        
        assert api_key_manager.check_permission(key, "read") is True
        assert api_key_manager.check_permission(key, "write") is True
    
    @pytest.mark.p1
    def test_check_permission_without_permission(self, api_key_manager):
        """Verify permission check fails without permission."""
        key, meta = api_key_manager.generate_key(
            "test",
            permissions=["read"]
        )
        
        assert api_key_manager.check_permission(key, "write") is False
        assert api_key_manager.check_permission(key, "delete") is False
    
    @pytest.mark.p1
    def test_check_permission_wildcard(self, api_key_manager):
        """Verify wildcard permission grants all."""
        key, meta = api_key_manager.generate_key(
            "test",
            permissions=["*"]
        )
        
        assert api_key_manager.check_permission(key, "read") is True
        assert api_key_manager.check_permission(key, "write") is True
        assert api_key_manager.check_permission(key, "delete") is True
        assert api_key_manager.check_permission(key, "anything") is True
    
    @pytest.mark.p1
    def test_check_permission_invalid_key(self, api_key_manager):
        """Verify permission check fails for invalid key."""
        assert api_key_manager.check_permission("invalid_key", "read") is False


class TestAPIKeyStatistics:
    """Test statistics and reporting."""
    
    @pytest.mark.p1
    def test_statistics_empty_manager(self, api_key_manager):
        """Verify statistics for empty manager."""
        stats = api_key_manager.get_statistics()
        
        assert stats["total_keys"] == 0
        assert stats["active_keys"] == 0
        assert stats["revoked_keys"] == 0
        assert stats["total_usage"] == 0
        assert stats["average_usage"] == 0
    
    @pytest.mark.p1
    def test_statistics_with_keys(self, api_key_manager):
        """Verify statistics calculation."""
        # Create 3 keys
        key1, meta1 = api_key_manager.generate_key("test1")
        key2, meta2 = api_key_manager.generate_key("test2")
        key3, meta3 = api_key_manager.generate_key("test3")
        
        # Use them
        api_key_manager.validate_key(key1)
        api_key_manager.validate_key(key1)
        api_key_manager.validate_key(key2)
        
        # Revoke one
        api_key_manager.revoke_key(meta3.key_id)
        
        stats = api_key_manager.get_statistics()
        
        assert stats["total_keys"] == 3
        assert stats["active_keys"] == 2
        assert stats["revoked_keys"] == 1
        assert stats["total_usage"] == 3
        assert stats["average_usage"] == 1.0  # 3 usages / 3 keys


class TestAPIKeyListing:
    """Test key listing and filtering."""
    
    @pytest.mark.p1
    def test_list_all_keys(self, api_key_manager):
        """Verify listing all keys."""
        key1, meta1 = api_key_manager.generate_key("test1")
        key2, meta2 = api_key_manager.generate_key("test2")
        
        keys = api_key_manager.list_keys()
        
        assert len(keys) == 2
        assert meta1 in keys
        assert meta2 in keys
    
    @pytest.mark.p1
    def test_list_keys_by_status(self, api_key_manager):
        """Verify filtering by status."""
        key1, meta1 = api_key_manager.generate_key("active1")
        key2, meta2 = api_key_manager.generate_key("active2")
        key3, meta3 = api_key_manager.generate_key("revoked1")
        
        api_key_manager.revoke_key(meta3.key_id)
        
        active_keys = api_key_manager.list_keys(status=KeyStatus.ACTIVE)
        revoked_keys = api_key_manager.list_keys(status=KeyStatus.REVOKED)
        
        assert len(active_keys) == 2
        assert len(revoked_keys) == 1
        assert meta3 in revoked_keys
    
    @pytest.mark.p1
    def test_list_keys_exclude_expired(self, api_key_manager):
        """Verify expired keys are excluded by default."""
        key1, meta1 = api_key_manager.generate_key("active")
        key2, meta2 = api_key_manager.generate_key("expired")
        
        # Manually expire one
        meta2.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        keys = api_key_manager.list_keys(include_expired=False)
        
        assert len(keys) == 1
        assert meta1 in keys
        assert meta2 not in keys
    
    @pytest.mark.p1
    def test_list_keys_include_expired(self, api_key_manager):
        """Verify expired keys can be included."""
        key1, meta1 = api_key_manager.generate_key("active")
        key2, meta2 = api_key_manager.generate_key("expired")
        
        meta2.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        keys = api_key_manager.list_keys(include_expired=True)
        
        assert len(keys) == 2
    
    @pytest.mark.p1
    def test_list_keys_sorted_by_created_at(self, api_key_manager):
        """Verify keys are sorted by creation time (newest first)."""
        key1, meta1 = api_key_manager.generate_key("oldest")
        key2, meta2 = api_key_manager.generate_key("middle")
        key3, meta3 = api_key_manager.generate_key("newest")
        
        keys = api_key_manager.list_keys()
        
        # Newest should be first
        assert keys[0].key_id == meta3.key_id
        assert keys[1].key_id == meta2.key_id
        assert keys[2].key_id == meta1.key_id


class TestAPIKeyInfo:
    """Test key information retrieval."""
    
    @pytest.mark.p1
    def test_get_key_info_existing_key(self, api_key_manager, sample_key):
        """Verify retrieving key info for existing key."""
        key, meta = sample_key
        
        info = api_key_manager.get_key_info(meta.key_id)
        
        assert info is not None
        assert info.key_id == meta.key_id
        assert info.name == meta.name
    
    @pytest.mark.p1
    def test_get_key_info_nonexistent_key(self, api_key_manager):
        """Verify retrieving key info for nonexistent key returns None."""
        info = api_key_manager.get_key_info("nonexistent")
        assert info is None
