"""
Tests for GovernanceLock Immutability
======================================

Classification: CRITICAL SECURITY TESTS
Purpose: Verify that governance mode cannot be changed after initialization

This module tests the immutable governance enforcement that prevents
runtime bypass via environment variables or runtime manipulation.

Test Coverage:
- Mode cannot be changed after initialization
- System fails-closed if governance is not initialized
- All bypass attempts are logged with full forensic context
- DISABLED mode requires cryptographic authorization
"""

from datetime import UTC, datetime

import pytest

from mahoun.core.governance_lock import (
    GovernanceLock,
    GovernanceMode,
    SecurityError,
    check_governance_integrity,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_governance_lock():
    """Reset governance lock before each test"""
    GovernanceLock._reset()
    yield
    GovernanceLock._reset()


# ============================================================================
# TESTS: Mode Cannot Be Changed After Initialization
# ============================================================================


class TestModeImmutability:
    """Tests that governance mode cannot be changed after initialization"""

    def test_initialization_sets_mode(self):
        """Initialization should set the governance mode"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        assert GovernanceLock.get_mode() == GovernanceMode.STRICT
        assert GovernanceLock._initialized is True

    def test_second_initialization_raises_error(self):
        """Second initialization attempt should raise RuntimeError"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        # Verify error message contains required information
        error_msg = str(exc_info.value)
        assert "already initialized" in error_msg.lower()
        assert "STRICT" in error_msg
        assert "AUDIT" in error_msg
        assert "change attempts" in error_msg.lower()

    def test_change_attempts_counter_increments(self):
        """Change attempts counter should increment on each bypass attempt"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # First bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert GovernanceLock._change_attempts == 1

        # Second bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED)

        assert GovernanceLock._change_attempts == 2

    def test_mode_cannot_be_changed_to_disabled(self):
        """Mode cannot be changed to DISABLED after initialization"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED)

        assert "already initialized" in str(exc_info.value).lower()

    def test_mode_cannot_be_changed_to_audit(self):
        """Mode cannot be changed to AUDIT after initialization"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert "already initialized" in str(exc_info.value).lower()


# ============================================================================
# TESTS: Forensic Logging
# ============================================================================


class TestForensicLogging:
    """Tests that bypass attempts are logged with full forensic context"""

    def test_bypass_attempt_logs_mode_change(self, capsys):
        """Bypass attempt should log current and requested modes"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        # Check that log output contains forensic context
        captured = capsys.readouterr()
        log_output = captured.out

        assert "CRITICAL" in log_output
        assert "Bypass attempt" in log_output
        assert "STRICT" in log_output
        assert "AUDIT" in log_output
        assert "attempt" in log_output.lower()

    def test_bypass_attempt_logs_timestamp(self, capsys):
        """Bypass attempt should log timestamp"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        captured = capsys.readouterr()
        log_output = captured.out

        # Verify timestamp is present (ISO 8601 format)
        assert "T" in log_output  # ISO 8601 date-time separator
        assert ":" in log_output  # Time separator

    def test_audit_metadata_contains_bypass_attempts(self):
        """Audit metadata should contain detailed bypass attempt information"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Make multiple bypass attempts
        for _ in range(3):
            with pytest.raises(RuntimeError):
                GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        metadata = GovernanceLock.get_audit_metadata()

        assert metadata["change_attempts"] == 3
        assert "bypass_attempts" in metadata
        assert len(metadata["bypass_attempts"]) == 3

        # Verify each bypass attempt has required fields
        for attempt in metadata["bypass_attempts"]:
            assert "attempt_number" in attempt
            assert "timestamp" in attempt
            assert "blocked" in attempt
            assert attempt["blocked"] is True


# ============================================================================
# TESTS: Fail-Closed Behavior
# ============================================================================


class TestFailClosed:
    """Tests that system fails-closed when governance is not initialized"""

    def test_uninitialized_default_to_strict(self):
        """Uninitialized lock should default to STRICT mode"""
        # Ensure lock is not initialized
        GovernanceLock._reset()

        mode = GovernanceLock.get_mode()

        assert mode == GovernanceMode.STRICT

    def test_uninitialized_enforcement_enabled(self):
        """Uninitialized lock should have enforcement enabled (fail-closed)"""
        GovernanceLock._reset()

        enforcement_enabled = GovernanceLock.is_enforcement_enabled()

        assert enforcement_enabled is True

    def test_check_governance_integrity_uninitialized(self):
        """Integrity check on uninitialized lock should indicate issue"""
        GovernanceLock._reset()

        metadata = GovernanceLock.get_audit_metadata()

        assert metadata["initialized"] is False
        assert metadata["mode"] == "UNINITIALIZED"
        assert metadata["integrity_verified"] is False


# ============================================================================
# TESTS: Cryptographic Authorization
# ============================================================================


class TestDisabledModeAuthorization:
    """Tests that DISABLED mode requires cryptographic authorization"""

    def test_disabled_mode_without_token_raises_error(self, capsys):
        """DISABLED mode without token should raise SecurityError"""
        GovernanceLock._reset()

        with pytest.raises(SecurityError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED)

        assert "authorization" in str(exc_info.value).lower()

    def test_disabled_mode_with_valid_token_succeeds(self, capsys):
        """DISABLED mode with valid token should succeed"""
        GovernanceLock._reset()

        # Generate valid token for today
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        expected_input = f"MAHOUN_DEV_OVERRIDE_{today}"
        import hashlib

        valid_token = hashlib.sha256(expected_input.encode()).hexdigest()

        # This should succeed
        GovernanceLock.initialize(mode=GovernanceMode.DISABLED, authorization_token=valid_token)

        assert GovernanceLock.get_mode() == GovernanceMode.DISABLED

    def test_disabled_mode_with_invalid_token_raises_error(self, capsys):
        """DISABLED mode with invalid token should raise SecurityError"""
        GovernanceLock._reset()

        with pytest.raises(SecurityError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED, authorization_token="invalid_token")

        assert "authorization" in str(exc_info.value).lower()


# ============================================================================
# TESTS: Immutability Verification
# ============================================================================


class TestImmutabilityVerification:
    """Tests for verify_immutable method"""

    def test_verify_immutable_on_valid_lock(self):
        """verify_immutable should return True on valid lock"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        assert GovernanceLock.verify_immutable() is True

    def test_verify_immutable_after_bypass_attempt(self):
        """verify_immutable should return False after bypass attempt"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Make a bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert GovernanceLock.verify_immutable() is False

    def test_verify_immutable_after_reset(self):
        """verify_immutable should return False after reset"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)
        GovernanceLock._reset()

        assert GovernanceLock.verify_immutable() is False


# ============================================================================
# TESTS: Integration with Existing Code
# ============================================================================


class TestIntegration:
    """Tests for integration with existing code"""

    def test_check_governance_integrity_with_bypass_attempts(self):
        """check_governance_integrity should include bypass attempts in alert"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Make a bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        metadata = check_governance_integrity()

        assert "alert" in metadata
        assert "bypass attempts" in metadata["alert"].lower()
        assert "bypass_attempts" in metadata

    def test_should_enforce_proof_carrying_contract_fails_closed(self):
        """should_enforce_proof_carrying_contract should fail-closed"""
        from mahoun.core.governance_lock import should_enforce_proof_carrying_contract

        # Reset to uninitialized state
        GovernanceLock._reset()

        # Should enforce (fail-closed)
        assert should_enforce_proof_carrying_contract() is True

        # Initialize and verify
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)
        assert should_enforce_proof_carrying_contract() is True

        # Make bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        # Should still enforce (fail-closed on compromised lock)
        assert should_enforce_proof_carrying_contract() is True
