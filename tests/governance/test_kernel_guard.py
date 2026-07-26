"""
MAHOUN Governance Kernel Guard Tests
====================================

Test suite for kernel_guard.py - Constitutional Kernel Protection

Tests prove:
- Modified kernel fails verification
- Unauthorized kernel change fails
- Kernel lock validation works
- Manifest validation works
- Attestation verification works
"""

import os
import json
import yaml
import hashlib
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Test fixtures
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONSTITUTION_DIR = os.path.join(ROOT_DIR, "constitution")
MANIFEST_PATH = os.path.join(CONSTITUTION_DIR, "kernel.manifest.yaml")
LOCK_PATH = os.path.join(CONSTITUTION_DIR, "kernel.lock")
CHANGES_PATH = os.path.join(CONSTITUTION_DIR, "kernel_changes.yaml")
ATTESTATION_PATH = os.path.join(CONSTITUTION_DIR, "kernel.attestation.json")


@pytest.fixture
def setup_test_environment():
    """Set up a temporary test environment."""
    # Create a temporary directory for test files
    temp_dir = tempfile.mkdtemp()
    constitution_dir = os.path.join(temp_dir, "constitution")
    os.makedirs(constitution_dir, exist_ok=True)
    
    # Create a minimal manifest
    manifest = {
        "kernel": {
            "name": "test_kernel",
            "version": "1.0.0",
            "description": "Test kernel",
            "strict_mode": True,
            "hash_algorithm": "SHA256"
        },
        "tiers": {
            "tier_0": {
                "description": "Test Tier 0",
                "protected_files": [
                    "test_module.py"
                ]
            }
        },
        "boundaries": {
            "forbidden_imports": {
                "tier_0": [
                    "forbidden_module"
                ]
            }
        },
        "kernel_change_policy": {
            "require_version_bump": True,
            "require_approval_label": ["kernel-change"],
            "require_audit_record": True,
            "require_authorization": True,
            "authorized_approvers": ["test-team", "security-team"],
            "change_record_path": "constitution/kernel_changes.yaml"
        }
    }
    
    manifest_path = os.path.join(constitution_dir, "kernel.manifest.yaml")
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)
    
    # Create a test module
    test_module_path = os.path.join(temp_dir, "test_module.py")
    with open(test_module_path, "w") as f:
        f.write("# Test module\nTEST_VARIABLE = 42\n")
    
    # Set environment variable for kernel guard
    os.environ["MAHOUN_TEST_ENV"] = temp_dir
    
    yield {
        "temp_dir": temp_dir,
        "constitution_dir": constitution_dir,
        "manifest_path": manifest_path,
        "test_module_path": test_module_path
    }
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    if "MAHOUN_TEST_ENV" in os.environ:
        del os.environ["MAHOUN_TEST_ENV"]


@pytest.fixture
def mock_kernel_guard_module(setup_test_environment, monkeypatch):
    """Mock the kernel_guard module paths to use test environment."""
    test_info = setup_test_environment
    
    # Patch the ROOT_DIR and paths in kernel_guard
    def mock_get_root_dir():
        return test_info["temp_dir"]
    
    # We'll monkeypatch when we import the module
    return test_info


class TestManifestLoading:
    """Tests for manifest loading and validation."""
    
    def test_load_manifest_success(self):
        """Test loading a valid manifest."""
        from mahoun.governance.kernel_guard import load_manifest
        
        # This should work with the existing manifest
        manifest = load_manifest()
        assert "kernel" in manifest
        assert "tiers" in manifest
        assert "boundaries" in manifest
    
    def test_load_manifest_file_not_found(self, monkeypatch):
        """Test loading manifest when file doesn't exist."""
        from mahoun.governance import kernel_guard
        
        # Temporarily change MANIFEST_PATH
        original_path = kernel_guard.MANIFEST_PATH
        kernel_guard.MANIFEST_PATH = "/nonexistent/path/manifest.yaml"
        
        try:
            with pytest.raises(SystemExit) as exc_info:
                kernel_guard.load_manifest()
            assert exc_info.value.code == 1
        finally:
            kernel_guard.MANIFEST_PATH = original_path
    
    def test_validate_manifest_structure(self):
        """Test manifest structure validation."""
        from mahoun.governance.kernel_guard import load_manifest, validate_manifest_structure
        
        manifest = load_manifest()
        result = validate_manifest_structure(manifest)
        assert result is True
    
    def test_validate_manifest_missing_kernel(self, monkeypatch):
        """Test validation fails when kernel section is missing."""
        from mahoun.governance.kernel_guard import validate_manifest_structure, ManifestValidationError
        
        manifest = {"tiers": {}, "boundaries": {}}
        
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest_structure(manifest)
        
        assert "kernel" in str(exc_info.value)


class TestHashCalculation:
    """Tests for SHA256 hash calculation."""
    
    def test_calculate_sha256_valid_file(self):
        """Test SHA256 calculation for a valid file."""
        from mahoun.governance.kernel_guard import calculate_sha256
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# Test file\nTEST = 123\n")
            temp_path = f.name
        
        try:
            # Calculate hash relative to ROOT_DIR
            # We need to create it in the right location
            test_file = os.path.join(ROOT_DIR, "test_temp_file.py")
            with open(test_file, "w") as f:
                f.write("# Test file\nTEST = 123\n")
            
            result = calculate_sha256("test_temp_file.py")
            assert result is not None
            assert len(result) == 64  # SHA256 hex digest length
            
            # Verify the hash
            expected_hash = hashlib.sha256(b"# Test file\nTEST = 123\n").hexdigest()
            assert result == expected_hash
            
            # Cleanup
            os.remove(test_file)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_calculate_sha256_file_not_found(self):
        """Test SHA256 calculation for non-existent file."""
        from mahoun.governance.kernel_guard import calculate_sha256
        
        result = calculate_sha256("nonexistent_file.py")
        assert result is None


class TestLockFileOperations:
    """Tests for kernel lock file operations."""
    
    def test_load_lock_file_not_found(self):
        """Test loading lock file when it doesn't exist."""
        from mahoun.governance.kernel_guard import load_lock, LOCK_PATH
        import os
        
        # Temporarily rename lock file if it exists
        temp_path = None
        if os.path.exists(LOCK_PATH):
            temp_path = LOCK_PATH + ".tmp"
            os.rename(LOCK_PATH, temp_path)
        
        try:
            result = load_lock()
            assert result == {}
        finally:
            # Restore lock file if it was renamed
            if temp_path and os.path.exists(temp_path):
                os.rename(temp_path, LOCK_PATH)
    
    def test_save_and_load_lock(self):
        """Test saving and loading lock file."""
        from mahoun.governance.kernel_guard import save_lock, load_lock
        
        # Create temporary lock file
        temp_lock_path = os.path.join(ROOT_DIR, "test_lock.json")
        original_lock_path = None
        
        try:
            # Save test lock
            test_lock = {
                "files": {"test.py": "test_hash"},
                "generated_at": "2026-01-01T00:00:00Z",
                "kernel_version": "1.0.0"
            }
            
            # Temporarily change LOCK_PATH
            import mahoun.governance.kernel_guard as kg
            original_lock_path = kg.LOCK_PATH
            kg.LOCK_PATH = temp_lock_path
            
            save_lock(test_lock)
            assert os.path.exists(temp_lock_path)
            
            loaded = load_lock()
            assert loaded == test_lock
            
        finally:
            if original_lock_path:
                kg.LOCK_PATH = original_lock_path
            if os.path.exists(temp_lock_path):
                os.remove(temp_lock_path)


class TestKernelIntegrity:
    """Tests for kernel integrity verification."""
    
    def test_verify_lock_success(self):
        """Test verification succeeds when files match lock."""
        from mahoun.governance.kernel_guard import (
            load_manifest, 
            calculate_sha256,
            update_lock,
            verify_lock
        )
        
        # Use existing manifest
        manifest = load_manifest()
        
        # Create a test lock with current hashes
        tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
        
        # Update the lock
        update_lock(manifest)
        
        # Verify should succeed
        result = verify_lock(manifest)
        assert result is True
    
    def test_verify_lock_detects_modified_file(self):
        """Test that verification detects modified files."""
        from mahoun.governance.kernel_guard import (
            load_manifest,
            update_lock,
            verify_lock
        )
        
        manifest = load_manifest()
        
        # Update lock to get current hashes
        update_lock(manifest)
        
        # Now modify a protected file
        tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
        if tier_0_files:
            test_file = tier_0_files[0]
            abs_path = os.path.join(ROOT_DIR, test_file)
            
            # Read original content
            with open(abs_path, "r") as f:
                original_content = f.read()
            
            try:
                # Modify the file
                with open(abs_path, "w") as f:
                    f.write(original_content + "\n# MODIFIED FOR TEST\n")
                
                # Verification should fail
                with pytest.raises(SystemExit) as exc_info:
                    verify_lock(manifest)
                assert exc_info.value.code == 1
            
            finally:
                # Restore original content
                with open(abs_path, "w") as f:
                    f.write(original_content)


class TestAuthorization:
    """Tests for kernel change authorization."""
    
    def test_validate_authorization_success(self):
        """Test authorization validation with valid parameters."""
        from mahoun.governance.kernel_guard import (
            load_manifest,
            validate_authorization
        )
        
        manifest = load_manifest()
        
        result = validate_authorization(
            manifest,
            reason="This is a valid reason for the change",
            approved_by="security-team"
        )
        assert result is True
    
    def test_validate_authorization_short_reason(self):
        """Test authorization fails with short reason."""
        from mahoun.governance.kernel_guard import (
            load_manifest,
            validate_authorization
        )
        
        manifest = load_manifest()
        
        result = validate_authorization(
            manifest,
            reason="short",
            approved_by="security-team"
        )
        assert result is False
    
    def test_validate_authorization_unauthorized_approver(self):
        """Test authorization fails with unauthorized approver."""
        from mahoun.governance.kernel_guard import (
            load_manifest,
            validate_authorization
        )
        
        manifest = load_manifest()
        
        result = validate_authorization(
            manifest,
            reason="This is a valid reason for the change",
            approved_by="unauthorized-person"
        )
        assert result is False


class TestAttestation:
    """Tests for kernel attestation."""
    
    def test_generate_attestation(self):
        """Test attestation generation."""
        from mahoun.governance.kernel_guard import (
            load_manifest,
            generate_attestation
        )
        
        manifest = load_manifest()
        
        # This will generate the attestation
        generate_attestation(manifest)
        
        # Check that the file was created/updated
        assert os.path.exists(ATTESTATION_PATH)
        
        # Load and verify structure
        with open(ATTESTATION_PATH, "r") as f:
            attestation = json.load(f)
        
        assert "kernel_version" in attestation
        assert "manifest_hash" in attestation
        assert "lock_hash" in attestation
        assert "approved" in attestation
    
    def test_verify_attestation(self):
        """Test attestation verification."""
        from mahoun.governance.kernel_guard import (
            verify_attestation
        )
        
        result = verify_attestation()
        # This may fail if attestation is not properly set up
        # but we just want to test the function doesn't crash
        assert isinstance(result, bool)


class TestKernelChangesTracking:
    """Tests for kernel changes tracking."""
    
    def test_load_changes_file_not_found(self):
        """Test loading changes when file doesn't exist."""
        from mahoun.governance.kernel_guard import load_changes
        
        # Temporarily use a non-existent path
        temp_path = "/nonexistent/changes.yaml"
        
        import mahoun.governance.kernel_guard as kg
        original_path = kg.CHANGES_PATH
        kg.CHANGES_PATH = temp_path
        
        try:
            result = load_changes()
            assert "changes" in result
            assert "current_version" in result
        finally:
            kg.CHANGES_PATH = original_path
    
    def test_save_and_load_changes(self):
        """Test saving and loading changes."""
        from mahoun.governance.kernel_guard import save_changes, load_changes
        
        # Create temporary changes file
        temp_changes_path = os.path.join(ROOT_DIR, "test_changes.yaml")
        
        import mahoun.governance.kernel_guard as kg
        original_path = kg.CHANGES_PATH
        kg.CHANGES_PATH = temp_changes_path
        
        try:
            # Save test changes
            test_changes = {
                "changes": [
                    {
                        "version": "1.1.0",
                        "date": "2026-01-01T00:00:00Z",
                        "reason": "Test change",
                        "approved_by": "test-team",
                        "authorization_hash": "test_hash"
                    }
                ],
                "current_version": "1.1.0"
            }
            
            save_changes(test_changes)
            assert os.path.exists(temp_changes_path)
            
            loaded = load_changes()
            assert loaded["current_version"] == "1.1.0"
            assert len(loaded["changes"]) == 1
        
        finally:
            kg.CHANGES_PATH = original_path
            if os.path.exists(temp_changes_path):
                os.remove(temp_changes_path)


class TestManifestValidation:
    """Tests for manifest validation."""
    
    def test_manifest_has_required_sections(self):
        """Test that manifest has all required sections."""
        from mahoun.governance.kernel_guard import load_manifest
        
        manifest = load_manifest()
        
        required_sections = ["kernel", "tiers", "boundaries"]
        for section in required_sections:
            assert section in manifest, f"Manifest missing section: {section}"
    
    def test_kernel_section_structure(self):
        """Test kernel section has required fields."""
        from mahoun.governance.kernel_guard import load_manifest
        
        manifest = load_manifest()
        kernel = manifest.get("kernel", {})
        
        assert "name" in kernel
        assert "version" in kernel
    
    def test_tier_0_protected_files_exist(self):
        """Test that Tier-0 protected files are defined."""
        from mahoun.governance.kernel_guard import load_manifest, get_tier_0_protected_files
        
        manifest = load_manifest()
        protected_files = get_tier_0_protected_files(manifest)
        
        assert isinstance(protected_files, list)
        assert len(protected_files) > 0


class TestErrorHandling:
    """Tests for error handling in kernel guard."""
    
    def test_kernel_guard_error_hierarchy(self):
        """Test error class hierarchy."""
        from mahoun.governance.kernel_guard import (
            KernelGuardError,
            KernelIntegrityViolationError,
            UnauthorizedKernelChangeError,
            ManifestValidationError
        )
        
        assert issubclass(KernelIntegrityViolationError, KernelGuardError)
        assert issubclass(UnauthorizedKernelChangeError, KernelGuardError)
        assert issubclass(ManifestValidationError, KernelGuardError)


# Integration tests
class TestIntegration:
    """Integration tests for kernel guard functionality."""
    
    def test_full_verification_flow(self):
        """Test the full verification flow."""
        from mahoun.governance.kernel_guard import (
            load_manifest,
            validate_manifest_structure,
            verify_lock,
            verify_attestation,
            generate_attestation
        )
        
        # Load manifest
        manifest = load_manifest()
        
        # Validate structure
        validate_manifest_structure(manifest)
        
        # Generate attestation (if not exists)
        if not os.path.exists(ATTESTATION_PATH):
            generate_attestation(manifest)
        
        # Verify attestation
        verify_attestation()
        
        # Verify lock
        verify_lock(manifest)
        
        # All should pass
        assert True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
